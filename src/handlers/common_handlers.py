from aiogram import Router,types
from aiogram.filters import Command
router = Router()

@router.message(Command("start"))
async def start(message: types.Message):
    await message.answer("🚀 Бот запущен! Работаем!")

@router.message(Command("/help"))
async def help_handler(message: types.Message):
    await message.answer("в разработке")