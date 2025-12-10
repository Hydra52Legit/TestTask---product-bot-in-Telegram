from typing import List, Optional

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import Card, User, WithdrawalRequest


class UserService:
    """Сервис для работы с пользователями и балансом."""

    @staticmethod
    async def get_or_create(
        session: AsyncSession,
        telegram_id: int,
        username: Optional[str],
        first_name: Optional[str],
        last_name: Optional[str],
        admin_ids: Optional[List[int]] = None,
    ) -> User:
        """Получить пользователя или создать нового."""
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            user = User(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                is_admin=telegram_id in (admin_ids or []),
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
        else:
            # Обновляем флаг админа, если изменился конфиг
            should_be_admin = telegram_id in (admin_ids or [])
            if user.is_admin != should_be_admin:
                user.is_admin = should_be_admin
                await session.commit()

        return user

    @staticmethod
    async def sync_admin_flags(session: AsyncSession, admin_ids: List[int]) -> None:
        """Установить флаг is_admin для всех пользователей согласно списку."""
        await session.execute(
            update(User)
            .values(is_admin=False)
            .where(User.is_admin.is_(True), User.telegram_id.not_in(admin_ids))
        )
        if admin_ids:
            await session.execute(
                update(User).values(is_admin=True).where(User.telegram_id.in_(admin_ids))
            )
        await session.commit()

    @staticmethod
    async def create_withdrawal_request(
        session: AsyncSession,
        user: User,
        amount: float,
        requisites: str,
        min_amount: float,
    ) -> WithdrawalRequest:
        """Создать заявку на вывод средств с валидацией."""
        if amount < min_amount:
            raise ValueError("Сумма меньше минимально допустимой")
        if amount > user.balance:
            raise ValueError("Недостаточно средств для вывода")
        if not requisites.strip():
            raise ValueError("Реквизиты не могут быть пустыми")

        request = WithdrawalRequest(
            amount=amount,
            requisites=requisites.strip(),
            user_id=user.id,
        )
        session.add(request)
        await session.commit()
        await session.refresh(request)
        return request

    @staticmethod
    async def get_statistics(session: AsyncSession):
        """Получить статистику по пользователям и карточкам."""
        stmt = (
            select(
                User.id,
                User.username,
                User.first_name,
                func.count(Card.id).label("total_cards"),
                func.sum(func.case((Card.is_approved.is_(True), 1), else_=0)).label(
                    "approved_cards"
                ),
                func.sum(func.case((Card.is_rejected.is_(True), 1), else_=0)).label(
                    "rejected_cards"
                ),
            )
            .join(Card, Card.user_id == User.id, isouter=True)
            .group_by(User.id)
            .order_by(User.id)
        )
        result = await session.execute(stmt)
        return result.all()
