from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder


def get_admin_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="Модерация"))
    builder.add(KeyboardButton(text="Статистика"))
    builder.add(KeyboardButton(text="Заявки на вывод"))
    builder.add(KeyboardButton(text="🔙 Назад"))
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)


def get_moderation_keyboard(current_index: int, total_count: int, card_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if current_index > 0:
        builder.add(InlineKeyboardButton(text="«", callback_data=f"mod_prev_{current_index}_{card_id}"))
    builder.add(InlineKeyboardButton(text="✅ Одобрить", callback_data=f"mod_approve_{current_index}_{card_id}"))
    builder.add(InlineKeyboardButton(text="❌ Отклонить", callback_data=f"mod_reject_{current_index}_{card_id}"))
    builder.add(InlineKeyboardButton(text="✏️ Изменить", callback_data=f"mod_edit_{current_index}_{card_id}"))
    if current_index < total_count - 1:
        builder.add(InlineKeyboardButton(text="»", callback_data=f"mod_next_{current_index}_{card_id}"))
    builder.adjust(2)
    return builder.as_markup()


def get_edit_attributes_keyboard(card_id: int) -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text=f"Название|{card_id}"))
    builder.add(KeyboardButton(text=f"Описание|{card_id}"))
    builder.add(KeyboardButton(text=f"Цена|{card_id}"))
    builder.add(KeyboardButton(text="❌ Отмена"))
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


def get_withdrawal_requests_keyboard(current_index: int, total_count: int, request_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if current_index > 0:
        builder.add(InlineKeyboardButton(text="«", callback_data=f"withdraw_prev_{current_index}_{request_id}"))
    builder.add(InlineKeyboardButton(text="💸 Выплата проведена", callback_data=f"withdraw_process_{current_index}_{request_id}"))
    if current_index < total_count - 1:
        builder.add(InlineKeyboardButton(text="»", callback_data=f"withdraw_next_{current_index}_{request_id}"))
    builder.adjust(1)
    return builder.as_markup()


def get_statistics_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="🔄 Обновить", callback_data="stats_refresh"))
    return builder.as_markup()

