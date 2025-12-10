import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from config import Config
from database.models import Base
from middlewares.db_middleware import DatabaseMiddleware
from filters.admin_filter import AdminFilter
from handlers import common_handlers
from utils.logger import setup_logger


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
    logger.info("Middleware зарегистрированы")

    # Регистрация фильтров
    dp.message.filter(AdminFilter())
    dp.callback_query.filter(AdminFilter())

    # Регистрация роутеров
    dp.include_router(common_handlers.router)
    # Здесь позже добавим другие роутеры

    logger.info("Бот запускается...")

    # Запуск бота
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот остановлен")
    except Exception as e:
        logging.error(f"Ошибка запуска: {e}")
        raise