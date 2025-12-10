from aiogram.filters import BaseFilter
from aiogram.types import Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import User


class UserExistsFilter(BaseFilter):
    """Фильтр для проверки существования пользователя"""

    async def __call__(
            self,
            message: Message,
            session: AsyncSession
    ) -> bool:
        user_id = message.from_user.id

        stmt = select(User).where(User.telegram_id == user_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        return user is not None