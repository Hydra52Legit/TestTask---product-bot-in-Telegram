import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InputMediaPhoto, Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import Card, User
from src.keyboards.card_keyboards import get_cards_keyboard
from src.services.card_service import CardService
from src.services.user_service import UserService
from src.utils.states import CardCreationStates

router = Router()
logger = logging.getLogger(__name__)


@router.message(F.text == "📦 Добавить карточку")
async def start_card_creation(message: Message, state: FSMContext):
    """Начало создания карточки."""
    await message.answer("Введите название товара:")
    await state.set_state(CardCreationStates.waiting_for_title)


@router.message(CardCreationStates.waiting_for_title)
async def process_title(message: Message, state: FSMContext):
    """Обработка названия товара."""
    await state.update_data(title=message.text)
    await message.answer("Введите описание товара:")
    await state.set_state(CardCreationStates.waiting_for_description)


@router.message(CardCreationStates.waiting_for_description)
async def process_description(message: Message, state: FSMContext):
    """Обработка описания товара."""
    await state.update_data(description=message.text)
    await message.answer("Введите цену товара (только число):")
    await state.set_state(CardCreationStates.waiting_for_price)


@router.message(CardCreationStates.waiting_for_price)
async def process_price(message: Message, state: FSMContext):
    """Обработка цены товара."""
    try:
        price = float(message.text.replace(",", "."))
        if price <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Пожалуйста, введите корректную цену (положительное число):")
        return

    await state.update_data(price=price)
    await message.answer("Отправьте фото товара (или /skip чтобы пропустить):")
    await state.set_state(CardCreationStates.waiting_for_photo)


@router.message(CardCreationStates.waiting_for_photo, F.photo)
async def process_photo(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    user: User | None = None,
):
    """Обработка фото товара."""
    data = await state.get_data()
    photo = message.photo[-1] if message.photo else None

    if user is None:
        user = await UserService.get_or_create(
            session=session,
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
        )

    await CardService.create_card(
        session=session,
        user_id=user.id,
        title=data["title"],
        description=data["description"],
        price=data["price"],
        photo_url=photo.file_id if photo else None,
        photo_file_id=photo.file_id if photo else None,
    )

    await message.answer(
        "✅ Карточка товара создана и отправлена на модерацию!\nОжидайте одобрения администратора."
    )
    await state.clear()


@router.message(CardCreationStates.waiting_for_photo)
async def validate_photo(message: Message):
    """Подсказка при некорректном формате фото."""
    await message.answer("Отправьте фото или используйте /skip чтобы пропустить.")


@router.message(Command("skip"), CardCreationStates.waiting_for_photo)
async def skip_photo(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    user: User | None = None,
):
    """Пропуск добавления фото."""
    data = await state.get_data()

    if user is None:
        user = await UserService.get_or_create(
            session=session,
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
        )

    await CardService.create_card(
        session=session,
        user_id=user.id,
        title=data["title"],
        description=data["description"],
        price=data["price"],
        photo_url=None,
    )

    await message.answer(
        "✅ Карточка товара создана и отправлена на модерацию!\nОжидайте одобрения администратора."
    )
    await state.clear()


@router.message(F.text == "👀 Посмотреть карточки")
async def show_cards(message: Message, session: AsyncSession):
    """Показ карточек товаров."""
    cards = await CardService.get_approved_cards(session=session, limit=100)

    if not cards:
        await message.answer("Пока нет доступных карточек товаров.")
        return

    card = cards[0]
    caption = f"📦 {card.title}\n\n{card.description}\n\n💰 Цена: {card.price} руб."

    if card.photo_url:
        await message.answer_photo(
            photo=card.photo_url,
            caption=caption,
            reply_markup=get_cards_keyboard(0, len(cards), card.id),
        )
    else:
        await message.answer(
            caption, reply_markup=get_cards_keyboard(0, len(cards), card.id)
        )


@router.callback_query(F.data.startswith("card_"))
async def handle_card_navigation(callback: CallbackQuery, session: AsyncSession):
    """Обработка навигации по карточкам."""
    _, action, index_str = callback.data.split("_")
    current_index = int(index_str)

    cards = await CardService.get_approved_cards(session=session, limit=100)
    if not cards:
        await callback.answer("Нет доступных карточек")
        return

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
        media = InputMediaPhoto(media=card.photo_url, caption=caption)
        await callback.message.edit_media(
            media=media, reply_markup=get_cards_keyboard(new_index, len(cards), card.id)
        )
    else:
        await callback.message.edit_caption(
            caption=caption,
            reply_markup=get_cards_keyboard(new_index, len(cards), card.id),
        )

    await callback.answer()