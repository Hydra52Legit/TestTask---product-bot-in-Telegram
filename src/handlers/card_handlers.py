import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InputMediaPhoto, Message
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from src.database.models import Card, User
from src.keyboards.card_keyboards import get_cards_keyboard, get_card_creation_cancel_keyboard
from src.services.card_service import CardService
from src.services.user_service import UserService
from src.utils.states import CardCreationStates

router = Router()
logger = logging.getLogger(__name__)


# ============= СОЗДАНИЕ КАРТОЧКИ =============

@router.message(F.text == "📦 Добавить карточку")
async def start_card_creation(message: Message, state: FSMContext):
    """Начало создания карточки."""
    await state.clear()
    await message.answer("Введите название товара:")
    await state.set_state(CardCreationStates.waiting_for_title)


@router.message(CardCreationStates.waiting_for_title)
async def process_title(message: Message, state: FSMContext):
    """Обработка названия товара."""
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("❌ Создание карточки отменено.")
        return

    if len(message.text) > 200:
        await message.answer("❌ Название слишком длинное (макс. 200 символов)")
        return

    await state.update_data(title=message.text)
    await message.answer("Введите описание товара:", reply_markup=get_card_creation_cancel_keyboard())
    await state.set_state(CardCreationStates.waiting_for_description)


@router.message(CardCreationStates.waiting_for_description)
async def process_description(message: Message, state: FSMContext):
    """Обработка описания товара."""
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("❌ Создание карточки отменено.")
        return

    if len(message.text) > 2000:
        await message.answer("❌ Описание слишком длинное (макс. 2000 символов)")
        return

    await state.update_data(description=message.text)
    await message.answer("Введите цену товара (только число):", reply_markup=get_card_creation_cancel_keyboard())
    await state.set_state(CardCreationStates.waiting_for_price)


@router.message(CardCreationStates.waiting_for_price)
async def process_price(message: Message, state: FSMContext):
    """Обработка цены товара."""
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("❌ Создание карточки отменено.")
        return

    try:
        price = float(message.text.replace(",", "."))
        if price <= 0:
            await message.answer("❌ Цена должна быть положительным числом!")
            return
        if price > 1000000:
            await message.answer("❌ Цена слишком высокая (макс. 1,000,000 руб.)")
            return

    except ValueError:
        await message.answer("❌ Пожалуйста, введите корректную цену (число, например: 999.99):")
        return

    await state.update_data(price=price)
    await message.answer(
        "Отправьте фото товара или используйте /skip чтобы пропустить:",
        reply_markup=get_card_creation_cancel_keyboard()
    )
    await state.set_state(CardCreationStates.waiting_for_photo)


# Обработка ФОТО - первым хендлером должен быть /skip
@router.message(Command("skip"), CardCreationStates.waiting_for_photo)
async def skip_photo_during_creation(
        message: Message,
        state: FSMContext,
        session: AsyncSession,
        user: User | None = None,
):
    """Пропуск добавления фото (команда /skip)."""
    data = await state.get_data()

    # Проверяем обязательные поля
    required_fields = ["title", "description", "price"]
    for field in required_fields:
        if field not in data:
            logger.error(f"Отсутствует поле {field} при создании карточки")
            await message.answer("❌ Произошла ошибка. Начните создание карточки заново.")
            await state.clear()
            return

    # Получаем или создаем пользователя
    current_user = user
    if current_user is None:
        try:
            current_user = await UserService.get_or_create(
                session=session,
                telegram_id=message.from_user.id,
                username=message.from_user.username,
                first_name=message.from_user.first_name,
                last_name=message.from_user.last_name,
            )
        except Exception as e:
            logger.error(f"Ошибка получения пользователя: {e}")
            await message.answer("❌ Ошибка регистрации. Попробуйте позже.")
            await state.clear()
            return

    # Создаем карточку без фото
    try:
        card = await CardService.create_card(
            session=session,
            user_id=current_user.id,
            title=data["title"],
            description=data["description"],
            price=data["price"],
            photo_url=None,
            photo_file_id=None,
        )

        logger.info(f"Создана карточка #{card.id} без фото, пользователь {current_user.telegram_id}")

        await message.answer(
            f"✅ Карточка товара создана и отправлена на модерацию!\n"
            f"Ожидайте одобрения администратора.\n\n"
            f"📦 Название: {data['title']}\n"
            f"💰 Цена: {data['price']:.2f} руб."
        )

    except Exception as e:
        logger.error(f"Ошибка создания карточки: {e}")
        await message.answer("❌ Произошла ошибка при создании карточки. Попробуйте позже.")

    finally:
        await state.clear()


# Обработка КНОПКИ ОТМЕНА в состоянии фото
@router.message(F.text == "❌ Отмена", CardCreationStates.waiting_for_photo)
async def cancel_during_photo(message: Message, state: FSMContext):
    """Отмена создания карточки при ожидании фото."""
    await state.clear()
    await message.answer("❌ Создание карточки отменено.")


# Обработка ФОТО (когда присылают фото)
@router.message(CardCreationStates.waiting_for_photo, F.photo)
async def process_photo_with_photo(
        message: Message,
        state: FSMContext,
        session: AsyncSession,
        user: User | None = None,
):
    """Обработка фото товара (когда фото есть)."""
    data = await state.get_data()

    # Проверяем обязательные поля
    required_fields = ["title", "description", "price"]
    for field in required_fields:
        if field not in data:
            logger.error(f"Отсутствует поле {field} при создании карточки")
            await message.answer("❌ Произошла ошибка. Начните создание карточки заново.")
            await state.clear()
            return

    # Получаем или создаем пользователя
    current_user = user
    if current_user is None:
        try:
            current_user = await UserService.get_or_create(
                session=session,
                telegram_id=message.from_user.id,
                username=message.from_user.username,
                first_name=message.from_user.first_name,
                last_name=message.from_user.last_name,
            )
        except Exception as e:
            logger.error(f"Ошибка получения пользователя: {e}")
            await message.answer("❌ Ошибка регистрации. Попробуйте позже.")
            await state.clear()
            return

    # Создаем карточку с фото
    try:
        photo = message.photo[-1]
        card = await CardService.create_card(
            session=session,
            user_id=current_user.id,
            title=data["title"],
            description=data["description"],
            price=data["price"],
            photo_url=photo.file_id,
            photo_file_id=photo.file_id,
        )

        logger.info(f"Создана карточка #{card.id} с фото, пользователь {current_user.telegram_id}")

        await message.answer(
            f"✅ Карточка товара создана и отправлена на модерацию!\n"
            f"Ожидайте одобрения администратора.\n\n"
            f"📦 Название: {data['title']}\n"
            f"💰 Цена: {data['price']:.2f} руб."
        )

    except Exception as e:
        logger.error(f"Ошибка создания карточки: {e}")
        await message.answer("❌ Произошла ошибка при создании карточки. Попробуйте позже.")

    finally:
        await state.clear()


# Обработка ЛЮБОГО другого текста в состоянии фото (подсказка)
@router.message(CardCreationStates.waiting_for_photo)
async def handle_other_input_during_photo(message: Message):
    """Обработка любого другого ввода в состоянии ожидания фото."""
    if message.text and not message.text.startswith("/"):
        await message.answer(
            "📷 Отправьте фото товара или:\n"
            "• Используйте /skip чтобы пропустить добавление фото\n"
            "• Используйте ❌ Отмена чтобы отменить создание карточки"
        )


# ============= ПРОСМОТР КАРТОЧЕК =============

@router.message(F.text == "👀 Посмотреть карточки")
async def show_cards(message: Message, session: AsyncSession):
    """Показ карточек товаров."""
    cards = await CardService.get_approved_cards(session=session, limit=100)
    if not cards:
        await message.answer("📭 Пока нет доступных карточек товаров.")
        return

    card = cards[0]
    caption = (
        f"📦 {card.title}\n\n"
        f"{card.description}\n\n"
        f"💰 Цена: {card.price} руб.\n"
        f"👤 Продавец: @{card.user.username if card.user and card.user.username else 'Не указан'}"
    )

    if card.photo_url:
        await message.answer_photo(
            photo=card.photo_url,
            caption=caption,
            reply_markup=get_cards_keyboard(0, len(cards), card.id),
        )
    else:
        await message.answer(
            caption,
            reply_markup=get_cards_keyboard(0, len(cards), card.id)
        )


@router.callback_query(F.data.startswith("card_"))
async def handle_card_navigation(callback: CallbackQuery, session: AsyncSession):
    """Обработка навигации по карточкам."""
    try:
        _, action, index_str = callback.data.split("_")
        current_index = int(index_str)

        cards = await CardService.get_approved_cards(session=session, limit=100)

        if not cards:
            await callback.answer("Нет доступных карточек")
            return

        # Определяем новый индекс
        if action == "prev":
            new_index = current_index - 1 if current_index > 0 else len(cards) - 1
        elif action == "next":
            new_index = current_index + 1 if current_index < len(cards) - 1 else 0
        else:
            await callback.answer()
            return

        card = cards[new_index]
        caption = (
            f"📦 {card.title}\n\n"
            f"{card.description}\n\n"
            f"💰 Цена: {card.price} руб.\n"
            f"👤 Продавец: @{card.user.username if card.user and card.user.username else 'Не указан'}"
        )

        if card.photo_url:
            media = InputMediaPhoto(media=card.photo_url, caption=caption)
            await callback.message.edit_media(
                media=media,
                reply_markup=get_cards_keyboard(new_index, len(cards), card.id)
            )
        else:
            await callback.message.edit_caption(
                caption=caption,
                reply_markup=get_cards_keyboard(new_index, len(cards), card.id),
            )

        await callback.answer()

    except Exception as e:
        logger.error(f"Ошибка навигации по карточкам: {e}")
        await callback.answer("❌ Произошла ошибка")


# ============= ОТМЕНА ДЛЯ ДРУГИХ СОСТОЯНИЙ =============

@router.message(F.text == "❌ Отмена")
async def cancel_any_state(message: Message, state: FSMContext):
    """Универсальный хендлер для отмены любого состояния."""
    current_state = await state.get_state()

    if current_state is None:
        await message.answer("⚠️ Нет активного процесса для отмены.")
        return

    # Определяем, в каком состоянии находимся
    state_name = str(current_state)

    if "CardCreationStates" in state_name:
        response = "❌ Создание карточки отменено."
    elif "BalanceStates" in state_name:
        response = "❌ Вывод средств отменено."
    elif "AdminStates" in state_name:
        response = "❌ Редактирование карточки отменено."
    else:
        response = "❌ Действие отменено."

    await state.clear()
    await message.answer(response)
    logger.info(f"Cancelled state: {state_name}")


# ============= КОМАНДА /SKIP ВНЕ СОСТОЯНИЯ =============

@router.message(Command("skip"))
async def skip_command_outside_state(message: Message, state: FSMContext):
    """Обработка /skip вне состояния создания карточки."""
    current_state = await state.get_state()

    if current_state != CardCreationStates.waiting_for_photo:
        await message.answer("ℹ️ Команда /skip доступна только при создании карточки для пропуска фото.")