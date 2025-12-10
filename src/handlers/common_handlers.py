from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.keyboards.common_keyboards import get_main_keyboard
from src.database.models import User

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message, session: AsyncSession):
    """Обработка команды /start"""
    user_id = message.from_user.id

    # Получаем пользователя из сессии (уже зарегистрирован через middleware)
    from sqlalchemy import select
    stmt = select(User).where(User.telegram_id == user_id)
    result = await session.execute(stmt)
    user = result.scalar_one()

    welcome_text = (
        "👋 Добро пожаловать в магазин карточек!\n\n"
        "Вы можете:\n"
        "📦 Добавить карточку товара\n"
        "👀 Просматривать карточки других пользователей\n"
        "💰 Пополнять баланс и выводить средства\n\n"
        "Используйте меню ниже для навигации."
    )

    await message.answer(
        welcome_text,
        reply_markup=get_main_keyboard(user.is_admin)
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Обработка команды /help"""
    help_text = (
        "📚 Помощь по боту:\n\n"
        "📦 <b>Добавить карточку</b> - создать карточку товара\n"
        "👀 <b>Посмотреть карточки</b> - просмотр товаров\n"
        "💰 <b>Баланс</b> - проверка баланса и вывод средств\n\n"
        "Администраторы также имеют доступ к админ-панели."
    )

    await message.answer(help_text)


@router.message(F.text == "🔙 Назад")
async def back_to_main(message: Message, user: User):
    """Возврат в главное меню"""
    await message.answer(
        "Главное меню:",
        reply_markup=get_main_keyboard(user.is_admin)
    )