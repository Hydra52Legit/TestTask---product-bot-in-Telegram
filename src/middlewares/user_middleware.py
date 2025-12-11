from datetime import datetime
from typing import Any, Awaitable, Callable, Dict, List, Optional
import logging

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject  # ← Добавили CallbackQuery
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import User


class UserMiddleware(BaseMiddleware):
    """Middleware для регистрации/получения пользователя."""

    def __init__(self, admin_ids: Optional[List[int]] = None):
        self.admin_ids = admin_ids or []

    async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: Dict[str, Any],
    ) -> Any:
        # Извлекаем from_user в зависимости от типа события
        if isinstance(event, (Message, CallbackQuery)):
            user_info = event.from_user
        else:
            # Для других типов событий пропускаем
            return await handler(event, data)

        if user_info is None:
            return await handler(event, data)

        session: AsyncSession = data["session"]
        user_id = user_info.id
        stmt = select(User).where(User.telegram_id == user_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            user = User(
                telegram_id=user_id,
                username=user_info.username,
                first_name=user_info.first_name,
                last_name=user_info.last_name,
                is_admin=user_id in self.admin_ids,
                created_at=datetime.utcnow(),
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            logging.getLogger(__name__).info("Создан пользователь %s (admin=%s)", user_id, user.is_admin)
        else:
            should_be_admin = user_id in self.admin_ids
            if user.is_admin != should_be_admin:
                user.is_admin = should_be_admin
                await session.commit()
                logging.getLogger(__name__).info("Флаг админа обновлен %s -> %s", user_id, should_be_admin)

        data["user"] = user
        return await handler(event, data)