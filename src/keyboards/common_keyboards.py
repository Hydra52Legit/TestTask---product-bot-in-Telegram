from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder


def get_main_keyboard(is_admin: bool = False) -> ReplyKeyboardMarkup:
    """Основное меню пользователя"""
    builder = ReplyKeyboardBuilder()

    builder.add(KeyboardButton(text="📦 Добавить карточку"))
    builder.add(KeyboardButton(text="👀 Посмотреть карточки"))
    builder.add(KeyboardButton(text="💰 Баланс"))

    if is_admin:
        builder.add(KeyboardButton(text="👨‍💼 Админ меню"))

    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)


def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура для отмены действия"""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="❌ Отмена"))
    return builder.as_markup(resize_keyboard=True)


def get_back_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура для возврата"""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="🔙 Назад"))
    return builder.as_markup(resize_keyboard=True)