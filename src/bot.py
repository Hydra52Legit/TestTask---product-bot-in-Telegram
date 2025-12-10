import asyncio
import logging
import sys
import os

# Добавляем путь к src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from config import Config
from database.models import Base
from middlewares.db_middleware import DatabaseMiddleware
from middlewares.user_middleware import UserMiddleware
from filters.admin_filter import AdminFilter
from utils.logger import setup_logger

# Импортируем все handlers
from handlers.common_handlers import router as common_router
from handlers.card_handlers import router as card_router
from handlers.payment_handlers import router as payment_router
from handlers.balance_handlers import router as balance_router
from handlers.admin_handlers import router as admin_router


async def main():
    """Основная функция запуска бота"""
    # Настройка логирования
    setup_logger()
    logger = logging.getLogger(__name__)

    # Загрузка конфигурации
    config = Config()
    logger.info("Конфигурация загружена")

    # Инициализация базы данных
    engine = create_async_engine(config.database_url, echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    # Создание таблиц
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("База данных инициализирована")

    # Инициализация бота
    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Регистрация middleware
    dp.update.middleware(DatabaseMiddleware(async_session))
    dp.update.middleware(UserMiddleware())
    logger.info("Middleware зарегистрированы")

    # Регистрация фильтров
    dp.message.filter(AdminFilter())
    dp.callback_query.filter(AdminFilter())

    # Регистрация роутеров (в правильном порядке!)
    dp.include_router(common_router)  # /start, /help
    dp.include_router(user_router)  # Регистрация
    dp.include_router(card_router)  # Карточки
    dp.include_router(payment_router)  # Платежи
    dp.include_router(balance_router)  # Баланс
    dp.include_router(admin_router)  # Админка

    logger.info("Все роутеры зарегистрированы")
    logger.info("Бот запускается...")

    # Запуск бота
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nБот остановлен")
    except Exception as e:
        logging.error(f"Ошибка запуска: {e}", exc_info=True)
        raise