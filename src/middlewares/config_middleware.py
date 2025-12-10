from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from src.config import Config


class ConfigMiddleware(BaseMiddleware):
    """Передает конфиг в контекст обработчиков."""

    def __init__(self, config: Config):
        self.config = config

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        data["config"] = self.config
        return await handler(event, data)

