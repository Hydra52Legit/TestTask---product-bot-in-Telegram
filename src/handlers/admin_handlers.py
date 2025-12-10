from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery, InputMediaPhoto
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from src.database.models import Card, User, WithdrawalRequest
from src.keyboards.admin_keyboards import (
    get_admin_keyboard,
    get_moderation_keyboard,
    get_withdrawal_requests_keyboard,
    get_statistics_keyboard
)
from src.utils.states import AdminStates

router = Router()


@router.message(Command("admin"))
async def admin_menu(message: Message):
    """Меню администратора"""
    await message.answer(
        "👨‍💼 Админ меню",
        reply_markup=get_admin_keyboard()
    )


@router.message(F.text == "Модерация")
async def show_moderation(message: Message, session: AsyncSession):
    """Показ карточек на модерации"""
    # Получение карточек на модерации
    stmt = select(Card).where(
        Card.is_approved == False,
        Card.is_rejected == False
    ).order_by(Card.created_at.desc())

    result = await session.execute(stmt)
    cards = result.scalars().all()

    if not cards:
        await message.answer("Нет карточек на модерации.")
        return

    card = cards[0]
    caption = (
        f"📦 {card.title}\n\n"
        f"📝 Описание: {card.description}\n\n"
        f"💰 Цена: {card.price} руб.\n"
        f"👤 Автор: @{card.user.username if card.user.username else 'Без username'}"
    )

    if card.photo_url:
        await message.answer_photo(
            photo=card.photo_url,
            caption=caption,
            reply_markup=get_moderation_keyboard(0, len(cards), card.id)
        )
    else:
        await message.answer(
            caption,
            reply_markup=get_moderation_keyboard(0, len(cards), card.id)
        )


@router.callback_query(F.data.startswith("mod_"))
async def handle_moderation(callback: CallbackQuery, session: AsyncSession):
    """Обработка модерации карточек"""
    action, index_str, card_id_str = callback.data.split("_")[1:]
    current_index = int(index_str)
    card_id = int(card_id_str)

    # Получение карточки
    stmt = select(Card).where(Card.id == card_id)
    result = await session.execute(stmt)
    card = result.scalar_one_or_none()

    if not card:
        await callback.answer("Карточка не найдена")
        return

    # Действия модерации
    if action == "approve":
        card.is_approved = True
        await session.commit()
        await callback.answer("✅ Карточка одобрена")
    elif action == "reject":
        card.is_rejected = True
        await session.commit()
        await callback.answer("❌ Карточка отклонена")
    elif action == "edit":
        await callback.message.answer(
            "Выберите атрибут для изменения:",
            reply_markup=get_edit_attributes_keyboard(card_id)
        )
        await callback.answer()
        return
    elif action in ["prev", "next"]:
        # Навигация
        stmt = select(Card).where(
            Card.is_approved == False,
            Card.is_rejected == False
        ).order_by(Card.created_at.desc())

        result = await session.execute(stmt)
        cards = result.scalars().all()

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
        caption = (
            f"📦 {card.title}\n\n"
            f"📝 Описание: {card.description}\n\n"
            f"💰 Цена: {card.price} руб.\n"
            f"👤 Автор: @{card.user.username if card.user.username else 'Без username'}"
        )

        if card.photo_url:
            media = InputMediaPhoto(
                media=card.photo_url,
                caption=caption
            )
            await callback.message.edit_media(
                media=media,
                reply_markup=get_moderation_keyboard(new_index, len(cards), card.id)
            )
        else:
            await callback.message.edit_caption(
                caption=caption,
                reply_markup=get_moderation_keyboard(new_index, len(cards), card.id)
            )
        await callback.answer()
        return

    # Обновление списка после модерации
    stmt = select(Card).where(
        Card.is_approved == False,
        Card.is_rejected == False
    ).order_by(Card.created_at.desc())

    result = await session.execute(stmt)
    cards = result.scalars().all()

    if cards:
        card = cards[0]
        caption = (
            f"📦 {card.title}\n\n"
            f"📝 Описание: {card.description}\n\n"
            f"💰 Цена: {card.price} руб.\n"
            f"👤 Автор: @{card.user.username if card.user.username else 'Без username'}"
        )

        if card.photo_url:
            media = InputMediaPhoto(
                media=card.photo_url,
                caption=caption
            )
            await callback.message.edit_media(
                media=media,
                reply_markup=get_moderation_keyboard(0, len(cards), card.id)
            )
        else:
            await callback.message.edit_caption(
                caption=caption,
                reply_markup=get_moderation_keyboard(0, len(cards), card.id)
            )
    else:
        await callback.message.answer("Нет карточек на модерации.")


@router.message(F.text == "Статистика")
async def show_statistics(message: Message, session: AsyncSession):
    """Показ статистики"""
    # Получение статистики
    stmt = select(
        User.id,
        User.username,
        User.first_name,
        func.count(Card.id).label("total_cards"),
        func.sum(func.case((Card.is_approved == True, 1), else_=0)).label("approved_cards"),
        func.sum(func.case((Card.is_rejected == True, 1), else_=0)).label("rejected_cards")
    ).join(Card, isouter=True).group_by(User.id)

    result = await session.execute(stmt)
    users_stats = result.all()

    if not users_stats:
        await message.answer("Нет данных для статистики.")
        return

    # Формирование сообщения
    stats_text = "📊 Статистика пользователей:\n\n"
    for stat in users_stats:
        user_info = f"👤 @{stat.username}" if stat.username else f"👤 {stat.first_name}"
        stats_text += (
            f"{user_info}:\n"
            f"   Всего карточек: {stat.total_cards or 0}\n"
            f"   Одобрено: {stat.approved_cards or 0}\n"
            f"   Отклонено: {stat.rejected_cards or 0}\n\n"
        )

    await message.answer(
        stats_text,
        reply_markup=get_statistics_keyboard()
    )


@router.message(F.text == "Заявки на вывод")
async def show_withdrawal_requests(message: Message, session: AsyncSession):
    """Показ заявок на вывод"""
    # Получение заявок
    stmt = select(WithdrawalRequest).where(
        WithdrawalRequest.is_processed == False
    ).order_by(WithdrawalRequest.created_at.desc())

    result = await session.execute(stmt)
    requests = result.scalars().all()

    if not requests:
        await message.answer("Нет заявок на вывод.")
        return

    request = requests[0]
    request_text = (
        f"💰 Заявка на вывод #{request.id}\n\n"
        f"👤 Пользователь: @{request.user.username if request.user.username else 'Без username'}\n"
        f"💵 Сумма: {request.amount} руб.\n"
        f"📋 Реквизиты: {request.requisites}\n"
        f"📅 Дата: {request.created_at.strftime('%d.%m.%Y %H:%M')}"
    )

    await message.answer(
        request_text,
        reply_markup=get_withdrawal_requests_keyboard(0, len(requests), request.id)
    )


@router.callback_query(F.data.startswith("withdraw_"))
async def handle_withdrawal_request(callback: CallbackQuery, session: AsyncSession):
    """Обработка заявок на вывод"""
    action, index_str, request_id_str = callback.data.split("_")[1:]
    current_index = int(index_str)
    request_id = int(request_id_str)

    # Получение заявки
    stmt = select(WithdrawalRequest).where(WithdrawalRequest.id == request_id)
    result = await session.execute(stmt)
    request = result.scalar_one_or_none()

    if not request:
        await callback.answer("Заявка не найдена")
        return

    if action == "process":
        # Обработка выплаты
        if request.user.balance >= request.amount:
            request.user.balance -= request.amount
            request.is_processed = True
            await session.commit()
            await callback.answer("✅ Выплата проведена")
        else:
            await callback.answer("❌ Недостаточно средств у пользователя")
            return

    # Обновление списка заявок
    stmt = select(WithdrawalRequest).where(
        WithdrawalRequest.is_processed == False
    ).order_by(WithdrawalRequest.created_at.desc())

    result = await session.execute(stmt)
    requests = result.scalars().all()

    if requests:
        if action in ["prev", "next"]:
            # Навигация
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

        request_text = (
            f"💰 Заявка на вывод #{request.id}\n\n"
            f"👤 Пользователь: @{request.user.username if request.user.username else 'Без username'}\n"
            f"💵 Сумма: {request.amount} руб.\n"
            f"📋 Реквизиты: {request.requisites}\n"
            f"📅 Дата: {request.created_at.strftime('%d.%m.%Y %H:%M')}"
        )

        await callback.message.edit_text(
            request_text,
            reply_markup=get_withdrawal_requests_keyboard(new_index, len(requests), request.id)
        )
    else:
        await callback.message.answer("Нет заявок на вывод.")

    await callback.answer()