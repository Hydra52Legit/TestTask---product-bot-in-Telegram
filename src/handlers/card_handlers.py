from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery, InputMediaPhoto
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import Card
from src.keyboards.card_keyboards import (
    get_cards_keyboard,
    get_card_management_keyboard
)
from src.utils.states import CardCreationStates

router = Router()


@router.message(F.text == "Добавить карточку")
async def start_card_creation(message: Message, state: FSMContext):
    """Начало создания карточки"""
    await message.answer("Введите название товара:")
    await state.set_state(CardCreationStates.waiting_for_title)


@router.message(CardCreationStates.waiting_for_title)
async def process_title(message: Message, state: FSMContext):
    """Обработка названия товара"""
    await state.update_data(title=message.text)
    await message.answer("Введите описание товара:")
    await state.set_state(CardCreationStates.waiting_for_description)


@router.message(CardCreationStates.waiting_for_description)
async def process_description(message: Message, state: FSMContext):
    """Обработка описания товара"""
    await state.update_data(description=message.text)
    await message.answer("Введите цену товара (только число):")
    await state.set_state(CardCreationStates.waiting_for_price)


@router.message(CardCreationStates.waiting_for_price)
async def process_price(message: Message, state: FSMContext):
    """Обработка цены товара"""
    try:
        price = float(message.text)
        if price <= 0:
            raise ValueError
        await state.update_data(price=price)
        await message.answer("Отправьте фото товара (или /skip чтобы пропустить):")
        await state.set_state(CardCreationStates.waiting_for_photo)
    except ValueError:
        await message.answer("Пожалуйста, введите корректную цену (положительное число):")


@router.message(CardCreationStates.waiting_for_photo)
async def process_photo(message: Message, state: FSMContext, session: AsyncSession):
    """Обработка фото товара"""
    data = await state.get_data()

    # Создание карточки
    card = Card(
        title=data['title'],
        description=data['description'],
        price=data['price'],
        user_id=message.from_user.id,
        photo_url=message.photo[-1].file_id if message.photo else None,
        is_approved=False
    )

    session.add(card)
    await session.commit()

    await message.answer(
        "✅ Карточка товара создана и отправлена на модерацию!\n"
        "Ожидайте одобрения администратора."
    )
    await state.clear()


@router.message(Command("skip"), CardCreationStates.waiting_for_photo)
async def skip_photo(message: Message, state: FSMContext, session: AsyncSession):
    """Пропуск добавления фото"""
    data = await state.get_data()

    # Создание карточки без фото
    card = Card(
        title=data['title'],
        description=data['description'],
        price=data['price'],
        user_id=message.from_user.id,
        photo_url=None,
        is_approved=False
    )

    session.add(card)
    await session.commit()

    await message.answer(
        "✅ Карточка товара создана и отправлена на модерацию!\n"
        "Ожидайте одобрения администратора."
    )
    await state.clear()


@router.message(F.text == "Посмотреть карточки")
async def show_cards(message: Message, session: AsyncSession):
    """Показ карточек товаров"""
    # Получение одобренных карточек
    from sqlalchemy import select
    stmt = select(Card).where(
        Card.is_approved == True
    ).order_by(Card.created_at.desc())

    result = await session.execute(stmt)
    cards = result.scalars().all()

    if not cards:
        await message.answer("Пока нет доступных карточек товаров.")
        return

    # Отправка первой карточки
    card = cards[0]
    caption = f"📦 {card.title}\n\n{card.description}\n\n💰 Цена: {card.price} руб."

    if card.photo_url:
        await message.answer_photo(
            photo=card.photo_url,
            caption=caption,
            reply_markup=get_cards_keyboard(0, len(cards), card.id)
        )
    else:
        await message.answer(
            caption,
            reply_markup=get_cards_keyboard(0, len(cards), card.id)
        )


@router.callback_query(F.data.startswith("card_"))
async def handle_card_navigation(callback: CallbackQuery, session: AsyncSession):
    """Обработка навигации по карточкам"""
    action, index_str = callback.data.split("_")[1], callback.data.split("_")[2]
    current_index = int(index_str)

    # Получение всех одобренных карточек
    from sqlalchemy import select
    stmt = select(Card).where(Card.is_approved == True).order_by(Card.created_at.desc())
    result = await session.execute(stmt)
    cards = result.scalars().all()

    if not cards:
        await callback.answer("Нет доступных карточек")
        return

    # Навигация
    if action == "prev" and current_index > 0:
        new_index = current_index - 1
    elif action == "next" and current_index < len(cards) - 1:
        new_index = current_index + 1
    else:
        await callback.answer()
        return

    card = cards[new_index]
    caption = f"📦 {card.title}\n\n{card.description}\n\n💰 Цена: {card.price} руб."

    if card.photo_url:
        media = InputMediaPhoto(
            media=card.photo_url,
            caption=caption
        )
        await callback.message.edit_media(
            media=media,
            reply_markup=get_cards_keyboard(new_index, len(cards), card.id)
        )
    else:
        await callback.message.edit_caption(
            caption=caption,
            reply_markup=get_cards_keyboard(new_index, len(cards), card.id)
        )

    await callback.answer()