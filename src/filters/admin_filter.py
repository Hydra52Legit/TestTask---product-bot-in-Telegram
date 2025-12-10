from typing import Union

from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import User


class AdminFilter(BaseFilter):
    """Фильтр для проверки администратора."""

    async def __call__(
        self, update: Union[Message, CallbackQuery], session: AsyncSession
    ) -> bool:
        if not hasattr(update, "from_user") or update.from_user is None:
            return False

        user_id = update.from_user.id

        stmt = select(User).where(User.telegram_id == user_id, User.is_admin.is_(True))
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        return user is not None