from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

from src.database.models import User

class UserMiddleware(BaseMiddleware):
    """Middleware для регистрации/получения пользователя"""

    async def __call__(
            self,
            handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
            event: Message,
            data: Dict[str, Any]
    ) -> Any:
        session: AsyncSession = data["session"]
        user_id = event.from_user.id

        # Проверяем существование пользователя
        stmt = select(User).where(User.telegram_id == user_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            # Регистрируем нового пользователя
            user = User(
                telegram_id=user_id,
                username=event.from_user.username,
                first_name=event.from_user.first_name,
                last_name=event.from_user.last_name,
                created_at=datetime.utcnow()
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)

        data["user"] = user
        return await handler(event, data)