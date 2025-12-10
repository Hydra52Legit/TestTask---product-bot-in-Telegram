from datetime import datetime
from typing import Any, Awaitable, Callable, Dict, List, Optional

from aiogram import BaseMiddleware
from aiogram.types import Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import User


class UserMiddleware(BaseMiddleware):
    """Middleware для регистрации/получения пользователя."""

    def __init__(self, admin_ids: Optional[List[int]] = None):
        self.admin_ids = admin_ids or []

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any],
    ) -> Any:
        # Некоторые обновления (service, chat_member) не имеют from_user
        if not hasattr(event, "from_user") or event.from_user is None:
            return await handler(event, data)

        session: AsyncSession = data["session"]
        user_id = event.from_user.id

        stmt = select(User).where(User.telegram_id == user_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            user = User(
                telegram_id=user_id,
                username=event.from_user.username,
                first_name=event.from_user.first_name,
                last_name=event.from_user.last_name,
                is_admin=user_id in self.admin_ids,
                created_at=datetime.utcnow(),
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
        else:
            should_be_admin = user_id in self.admin_ids
            if user.is_admin != should_be_admin:
                user.is_admin = should_be_admin
                await session.commit()

        data["user"] = user
        return await handler(event, data)