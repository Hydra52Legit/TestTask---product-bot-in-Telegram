import logging

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import Config
from src.database.models import User
from src.keyboards.balance_keyboards import get_balance_keyboard, get_cancel_reply_keyboard
from src.services.user_service import UserService
from src.utils.states import BalanceStates

router = Router()
logger = logging.getLogger(__name__)


@router.message(F.text == "💰 Баланс")
async def show_balance(message: Message, session: AsyncSession, user: User | None = None):
    """Показывает баланс и действия."""
    current_user = user
    if current_user is None:
        from sqlalchemy import select
        result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        current_user = result.scalar_one_or_none()

    balance_value = current_user.balance if current_user else 0.0
    await message.answer(
        f"Ваш баланс: {balance_value:.2f} руб.",
        reply_markup=get_balance_keyboard(),
    )


@router.callback_query(F.data == "balance_refresh")
async def refresh_balance(callback: CallbackQuery, user: User):
    await callback.message.edit_text(
        f"Ваш баланс: {user.balance:.2f} руб.",
        reply_markup=get_balance_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "balance_withdraw")
async def start_withdraw(callback: CallbackQuery, state: FSMContext):
    """Запускает сценарий вывода средств."""
    await state.set_state(BalanceStates.waiting_for_withdrawal_amount)
    await callback.message.answer(
        "Введите сумму для вывода:",
        reply_markup=get_cancel_reply_keyboard(),
    )
    await callback.answer()


@router.message(BalanceStates.waiting_for_withdrawal_amount)
async def process_withdraw_amount(
    message: Message, state: FSMContext, session: AsyncSession, config: Config, user: User | None = None
):
    """Проверяем сумму вывода."""
    # Подстраховка если user не был внедрен
    current_user = user
    if current_user is None:
        from sqlalchemy import select
        result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        current_user = result.scalar_one_or_none()
        if current_user is None:
            await message.answer("Пользователь не найден, отправьте /start и попробуйте снова.")
            return

    try:
        amount = float(message.text.replace(",", "."))
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Введите корректную сумму (положительное число).")
        return

    if amount < config.withdrawal_min_amount:
        await message.answer(
            f"Минимальная сумма вывода: {config.withdrawal_min_amount:.2f} руб."
        )
        return
    if amount > current_user.balance:
        await message.answer("Недостаточно средств на балансе.")
        return

    await state.update_data(amount=amount)
    await state.set_state(BalanceStates.waiting_for_withdrawal_requisites)
    await message.answer("Введите реквизиты для вывода (карта, кошелек и т.п.):")


@router.message(BalanceStates.waiting_for_withdrawal_requisites)
async def process_withdraw_requisites(
    message: Message, state: FSMContext, session: AsyncSession, config: Config, user: User | None = None
):
    """Создаем заявку на вывод."""
    # Подстраховка если user не был внедрен
    current_user = user
    if current_user is None:
        from sqlalchemy import select
        result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        current_user = result.scalar_one_or_none()
        if current_user is None:
            await message.answer("Пользователь не найден, отправьте /start и попробуйте снова.")
            await state.clear()
            return

    data = await state.get_data()
    amount = data.get("amount")

    try:
        request = await UserService.create_withdrawal_request(
            session=session,
            user=current_user,
            amount=amount,
            requisites=message.text,
            min_amount=config.withdrawal_min_amount,
        )
    except ValueError as exc:
        await message.answer(str(exc))
        await state.clear()
        return

    await state.clear()
    await message.answer(
        f"Заявка на вывод на сумму {request.amount:.2f} руб. создана и отправлена администратору."
    )
    logger.info("Withdrawal request %s created for user %s", request.id, current_user.id)


@router.message(F.text == "❌ Отмена")
async def cancel_withdraw(message: Message, state: FSMContext):
    """Отменяет сценарий вывода."""
    current_state = await state.get_state()

    # Проверяем что мы в состоянии вывода (опционально)
    if current_state and current_state.startswith("BalanceStates"):
        await state.clear()
        await message.answer("Вывод средств отменен.")
    else:
        await message.answer("Нет активного процесса вывода для отмены.")

