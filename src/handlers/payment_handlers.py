import logging
from typing import Optional

from aiogram import F, Router
from aiogram.types import CallbackQuery, LabeledPrice, Message, PreCheckoutQuery
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import Config
from src.database.models import Card, User
from src.services.payment_service import PaymentService

router = Router()
logger = logging.getLogger(__name__)


async def _get_card(session: AsyncSession, card_id: int) -> Optional[Card]:
    stmt = select(Card).where(Card.id == card_id, Card.is_approved.is_(True))
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


@router.callback_query(F.data.startswith("buy_"))
async def handle_buy(callback: CallbackQuery, session: AsyncSession, config: Config, user: User):
    """Запрос на покупку карточки: отправляем инвойс."""
    card_id = int(callback.data.split("_")[1])
    card = await _get_card(session, card_id)
    if not card:
        await callback.answer("Карточка недоступна")
        return

    if not config.payment_provider_token:
        await callback.answer("Оплата временно недоступна")
        logger.warning("Payment provider token is not configured")
        return

    purchase = await PaymentService.create_invoice(
        session=session, user_id=user.id, card_id=card.id, amount=card.price
    )
    prices = [LabeledPrice(label=card.title[:32], amount=int(card.price * 100))]

    await callback.bot.send_invoice(
        chat_id=callback.from_user.id,
        title=card.title,
        description=card.description[:200],
        provider_token=config.payment_provider_token,
        currency="RUB",
        prices=prices,
        payload=purchase.invoice_id,
    )
    await callback.answer("Счет выставлен")


@router.pre_checkout_query()
async def pre_checkout_handler(pre_checkout_query: PreCheckoutQuery):
    """Подтверждаем готовность принять платеж."""
    await pre_checkout_query.answer(ok=True)


@router.message(F.content_type == "successful_payment")
async def successful_payment(message: Message, session: AsyncSession):
    """Отмечаем покупку оплаченной и обновляем баланс продавца."""
    payload = message.successful_payment.invoice_payload
    is_processed = await PaymentService.process_payment(session, payload)
    if is_processed:
        await message.answer("Спасибо за покупку! Продавец уже получил оплату.")
        logger.info("Payment processed for invoice %s", payload)
    else:
        await message.answer("Не удалось обработать платеж. Поддержка уведомлена.")
        logger.error("Failed to process payment for invoice %s", payload)

