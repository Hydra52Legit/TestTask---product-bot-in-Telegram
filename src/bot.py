import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.config import Config
from src.database.models import Base
from src.middlewares.config_middleware import ConfigMiddleware
from src.middlewares.db_middleware import DatabaseMiddleware
from src.middlewares.user_middleware import UserMiddleware
from src.services.user_service import UserService
from src.utils.logger import setup_logger

# Импортируем все handlers
from src.handlers.common_handlers import router as common_router
from src.handlers.card_handlers import router as card_router
from src.handlers.payment_handlers import router as payment_router
from src.handlers.balance_handlers import router as balance_router
from src.handlers.admin_handlers import router as admin_router


async def main():
    """Основная функция запуска бота."""
    setup_logger()
    logger = logging.getLogger(__name__)

    config = Config()
    logger.info("Конфигурация загружена")

    engine = create_async_engine(config.database_url, echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("База данных инициализирована")

    # Синхронизируем флаги админов с конфигом
    async with async_session() as session:
        await UserService.sync_admin_flags(session, config.admin_ids_list)
    logger.info("Админы синхронизированы: %s", config.admin_ids_list)

    bot = Bot(token=config.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Middleware порядок важен: конфиг -> БД -> пользователь
    dp.update.middleware(ConfigMiddleware(config))
    dp.update.middleware(DatabaseMiddleware(async_session))
    dp.update.middleware(UserMiddleware(config.admin_ids_list))
    logger.info("Middleware зарегистрированы")

    dp.include_router(common_router)
    dp.include_router(card_router)
    dp.include_router(payment_router)
    dp.include_router(balance_router)
    dp.include_router(admin_router)

    logger.info("Все роутеры зарегистрированы")
    logger.info("Бот запускается...")

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nБот остановлен")
    except Exception as e:  # noqa: BLE001
        logging.error(f"Ошибка запуска: {e}", exc_info=True)
        raise