from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder


def get_cards_keyboard(
        current_index: int,
        total_count: int,
        card_id: int
) -> InlineKeyboardMarkup:
    """Клавиатура для навигации по карточкам"""
    builder = InlineKeyboardBuilder()

    if current_index > 0:
        builder.add(InlineKeyboardButton(
            text="« Назад",
            callback_data=f"card_prev_{current_index}"
        ))

    builder.add(InlineKeyboardButton(
        text=f"🛒 Купить",
        callback_data=f"buy_{card_id}"
    ))

    if current_index < total_count - 1:
        builder.add(InlineKeyboardButton(
            text="Вперед »",
            callback_data=f"card_next_{current_index}"
        ))

    builder.adjust(2)
    return builder.as_markup()


def get_buy_confirmation_keyboard(card_id: int) -> InlineKeyboardMarkup:
    """Подтверждение покупки"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="✅ Подтвердить покупку",
        callback_data=f"confirm_buy_{card_id}"
    ))
    builder.add(InlineKeyboardButton(
        text="❌ Отмена",
        callback_data="cancel_buy"
    ))
    return builder.as_markup()

def get_card_creation_cancel_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура для отмены создания карточки"""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="❌ Отмена"))
    return builder.as_markup(resize_keyboard=True)