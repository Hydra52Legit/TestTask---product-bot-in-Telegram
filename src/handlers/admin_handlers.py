import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InputMediaPhoto, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.database.models import Card, WithdrawalRequest, User
from src.keyboards.admin_keyboards import (
    get_admin_keyboard,
    get_edit_attributes_keyboard,
    get_moderation_keyboard,
    get_statistics_keyboard,
    get_withdrawal_requests_keyboard,
)
from src.services.card_service import CardService
from src.services.user_service import UserService
from src.utils.states import AdminStates

router = Router()
logger = logging.getLogger(__name__)


async def _check_admin(session: AsyncSession, user_id: int) -> bool:
    """Проверка является ли пользователь админом"""
    stmt = select(User).where(
        User.telegram_id == user_id,
        User.is_admin == True
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none() is not None


async def _get_pending_cards(session: AsyncSession):
    return await CardService.get_cards_for_moderation(session)


async def _format_card_caption(card: Card) -> str:
    author = f"@{card.user.username}" if card.user and card.user.username else "Без username"
    return (
        f"📦 {card.title}\n\n"
        f"📝 Описание: {card.description}\n\n"
        f"💰 Цена: {card.price} руб.\n"
        f"👤 Автор: {author}"
    )


def _format_withdraw_request(request: WithdrawalRequest) -> str:
    return (
        f"💰 Заявка на вывод #{request.id}\n\n"
        f"👤 Пользователь: @{request.user.username if request.user.username else 'Без username'}\n"
        f"💵 Сумма: {request.amount} руб.\n"
        f"📋 Реквизиты: {request.requisites}\n"
        f"📅 Дата: {request.created_at.strftime('%d.%m.%Y %H:%M')}"
    )


async def _build_stats(session: AsyncSession) -> str:
    users_stats = await UserService.get_statistics(session)
    if not users_stats:
        return "Нет данных для статистики."

    stats_text = "📊 Статистика пользователей:\n\n"
    for stat in users_stats:
        user_info = f"👤 @{stat.username}" if stat.username else f"👤 {stat.first_name}"
        stats_text += (
            f"{user_info}:\n"
            f"   Всего карточек: {stat.total_cards or 0}\n"
            f"   Одобрено: {stat.approved_cards or 0}\n"
            f"   Отклонено: {stat.rejected_cards or 0}\n\n"
        )
    return stats_text


# ============= ОСНОВНЫЕ ХЕНДЛЕРЫ =============

@router.message(Command("admin"))
@router.message(F.text == "👨‍💼 Админ меню")
async def admin_menu(message: Message, session: AsyncSession):
    """Меню администратора."""
    if not await _check_admin(session, message.from_user.id):
        await message.answer("❌ У вас нет доступа к админ-панели")
        return
    await message.answer("👨‍💼 Админ меню", reply_markup=get_admin_keyboard())


@router.message(F.text == "Модерация")
async def show_moderation(message: Message, session: AsyncSession):
    """Показ карточек на модерации."""
    if not await _check_admin(session, message.from_user.id):
        await message.answer("❌ У вас нет доступа к админ-панели")
        return

    cards = await _get_pending_cards(session)
    if not cards:
        await message.answer("Нет карточек на модерации.")
        return

    card = cards[0]
    caption = await _format_card_caption(card)

    if card.photo_url:
        await message.answer_photo(
            photo=card.photo_url,
            caption=caption,
            reply_markup=get_moderation_keyboard(0, len(cards), card.id),
        )
    else:
        await message.answer(
            caption, reply_markup=get_moderation_keyboard(0, len(cards), card.id)
        )


@router.message(F.text == "Статистика")
async def show_statistics(message: Message, session: AsyncSession):
    """Показ статистики."""
    if not await _check_admin(session, message.from_user.id):
        await message.answer("❌ У вас нет доступа к админ-панели")
        return

    stats_text = await _build_stats(session)
    await message.answer(stats_text, reply_markup=get_statistics_keyboard())


@router.message(F.text == "Заявки на вывод")
async def show_withdrawal_requests(message: Message, session: AsyncSession):
    """Показ заявок на вывод."""
    if not await _check_admin(session, message.from_user.id):
        await message.answer("❌ У вас нет доступа к админ-панели")
        return

    stmt = (
        select(WithdrawalRequest)
        .options(selectinload(WithdrawalRequest.user))
        .where(WithdrawalRequest.is_processed.is_(False))
        .order_by(WithdrawalRequest.created_at.desc())
    )
    requests = (await session.execute(stmt)).scalars().all()

    if not requests:
        await message.answer("Нет заявок на вывод.")
        return

    request = requests[0]
    request_text = _format_withdraw_request(request)

    await message.answer(
        request_text,
        reply_markup=get_withdrawal_requests_keyboard(0, len(requests), request.id),
    )


# ============= ХЕНДЛЕРЫ СОСТОЯНИЙ  =============

@router.message(F.text == "❌ Отмена")
async def cancel_admin_action(message: Message, state: FSMContext):
    """Универсальная отмена для админки"""
    current_state = await state.get_state()

    if current_state is None:
        await message.answer("Нет активного действия для отмены.")
        return

    # Проверяем какое состояние
    if current_state == AdminStates.editing_card_attribute:
        await message.answer("✏️ Редактирование атрибута отменено.")
    elif current_state == AdminStates.waiting_for_new_value:
        await message.answer("📝 Ввод нового значения отменен.")
    else:
        await message.answer("❌ Действие отменено.")

    await state.clear()


@router.message(AdminStates.editing_card_attribute)
async def choose_attribute(message: Message, state: FSMContext):
    """Выбор атрибута для редактирования."""
    # Уберите проверку "|" - теперь это делается в callback
    # Просто принимаем текст как название атрибута
    attribute_map = {
        "Название": "title",
        "Описание": "description",
        "Цена": "price",
    }

    attribute = attribute_map.get(message.text)
    if not attribute:
        await message.answer("❌ Выберите атрибут из предложенных вариантов или нажмите '❌ Отмена'.")
        return

    data = await state.get_data()
    card_id = data.get("card_id")

    if not card_id:
        await message.answer("❌ Ошибка: карточка не найдена.")
        await state.clear()
        return

    await state.update_data(attribute=attribute)
    await state.set_state(AdminStates.waiting_for_new_value)
    await message.answer(f"Введите новое значение для '{message.text}':")


@router.message(AdminStates.waiting_for_new_value)
async def apply_new_value(message: Message, state: FSMContext, session: AsyncSession):
    """Применение нового значения к карточке."""
    data = await state.get_data()
    card_id = data.get("card_id")
    attribute = data.get("attribute")

    if not card_id or not attribute:
        await message.answer("❌ Ошибка: данные не найдены.")
        await state.clear()
        return

    # Валидация цены, если это цена
    if attribute == "price":
        try:
            price = float(message.text)
            if price <= 0:
                await message.answer("❌ Цена должна быть положительным числом.")
                return
        except ValueError:
            await message.answer("❌ Введите корректное число для цены.")
            return

    updated = await CardService.update_card_attribute(
        session=session,
        card_id=card_id,
        attribute=attribute,
        value=message.text
    )

    if not updated:
        await message.answer("❌ Не удалось обновить карточку.")
    else:
        await message.answer("✅ Карточка успешно обновлена!")

    await state.clear()


# ============= CALLBACK ХЕНДЛЕРЫ =============

@router.callback_query(F.data.startswith("mod_"))
async def handle_moderation(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Обработка модерации карточек."""
    if not await _check_admin(session, callback.from_user.id):
        await callback.answer("❌ У вас нет доступа")
        return

    action, index_str, card_id_str = callback.data.split("_")[1:]
    current_index = int(index_str)
    card_id = int(card_id_str)

    card = await CardService.get_card_by_id(session, card_id)
    if not card:
        await callback.answer("Карточка не найдена")
        return

    if action == "approve":
        await CardService.approve_card(session, card_id)
        await callback.answer("✅ Карточка одобрена")
    elif action == "reject":
        await CardService.reject_card(session, card_id)
        await callback.answer("❌ Карточка отклонена")
    elif action == "edit":
        await state.set_state(AdminStates.editing_card_attribute)
        await state.update_data(card_id=card_id)

        # Отправляем клавиатуру с кнопками выбора атрибута
        await callback.message.answer(
            "Выберите атрибут для изменения:",
            reply_markup=get_edit_attributes_keyboard(card_id)
        )
        await callback.answer()
        return
    elif action in ["prev", "next"]:
        cards = await _get_pending_cards(session)
        if not cards:
            await callback.answer("Нет карточек на модерации")
            return

        if action == "prev" and current_index > 0:
            new_index = current_index - 1
        elif action == "next" and current_index < len(cards) - 1:
            new_index = current_index + 1
        else:
            await callback.answer()
            return

        card = cards[new_index]
        caption = await _format_card_caption(card)

        if card.photo_url:
            media = InputMediaPhoto(media=card.photo_url, caption=caption)
            await callback.message.edit_media(
                media=media,
                reply_markup=get_moderation_keyboard(new_index, len(cards), card.id),
            )
        else:
            await callback.message.edit_caption(
                caption=caption,
                reply_markup=get_moderation_keyboard(new_index, len(cards), card.id),
            )
        await callback.answer()
        return

    # Обновляем список после одобрения/отклонения
    cards = await _get_pending_cards(session)
    if cards:
        card = cards[0]
        caption = await _format_card_caption(card)
        if card.photo_url:
            media = InputMediaPhoto(media=card.photo_url, caption=caption)
            await callback.message.edit_media(
                media=media, reply_markup=get_moderation_keyboard(0, len(cards), card.id)
            )
        else:
            await callback.message.edit_caption(
                caption=caption, reply_markup=get_moderation_keyboard(0, len(cards), card.id)
            )
    else:
        await callback.message.answer("✅ Нет карточек на модерации.")

    await callback.answer()


@router.callback_query(F.data == "stats_refresh")
async def refresh_stats(callback: CallbackQuery, session: AsyncSession):
    if not await _check_admin(session, callback.from_user.id):
        await callback.answer("❌ У вас нет доступа")
        return

    stats_text = await _build_stats(session)
    await callback.message.edit_text(stats_text, reply_markup=get_statistics_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("withdraw_"))
async def handle_withdrawal_request(callback: CallbackQuery, session: AsyncSession):
    """Обработка заявок на вывод."""
    if not await _check_admin(session, callback.from_user.id):
        await callback.answer("❌ У вас нет доступа")
        return

    action, index_str, request_id_str = callback.data.split("_")[1:]
    current_index = int(index_str)
    request_id = int(request_id_str)

    stmt = (
        select(WithdrawalRequest)
        .options(selectinload(WithdrawalRequest.user))
        .where(WithdrawalRequest.id == request_id)
    )
    request = (await session.execute(stmt)).scalar_one_or_none()

    if not request:
        await callback.answer("Заявка не найдена")
        return

    if action == "process":
        if request.user.balance >= request.amount:
            request.user.balance -= request.amount
            request.is_processed = True
            await session.commit()
            await callback.answer("✅ Выплата проведена")
        else:
            await callback.answer("❌ Недостаточно средств у пользователя")
            return

    # Обновляем список заявок
    stmt = (
        select(WithdrawalRequest)
        .options(selectinload(WithdrawalRequest.user))
        .where(WithdrawalRequest.is_processed.is_(False))
        .order_by(WithdrawalRequest.created_at.desc())
    )
    requests = (await session.execute(stmt)).scalars().all()

    if requests:
        if action in ["prev", "next"]:
            if action == "prev" and current_index > 0:
                new_index = current_index - 1
            elif action == "next" and current_index < len(requests) - 1:
                new_index = current_index + 1
            else:
                await callback.answer()
                return
            request = requests[new_index]
        else:
            new_index = 0
            request = requests[0]

        request_text = _format_withdraw_request(request)

        await callback.message.edit_text(
            request_text,
            reply_markup=get_withdrawal_requests_keyboard(new_index, len(requests), request.id),
        )
    else:
        await callback.message.answer("✅ Нет заявок на вывод.")

    await callback.answer()