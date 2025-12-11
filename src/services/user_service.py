import logging
from typing import List, Optional

from sqlalchemy import func, select, update
from sqlalchemy import Integer
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import Card, User, WithdrawalRequest

logger = logging.getLogger(__name__)


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
            logger.info("Создан пользователь %s (admin=%s)", telegram_id, user.is_admin)
        else:
            # Обновляем флаг админа, если изменился конфиг
            should_be_admin = telegram_id in (admin_ids or [])
            if user.is_admin != should_be_admin:
                user.is_admin = should_be_admin
                await session.commit()
                logger.info("Обновлен флаг админа для %s -> %s", telegram_id, should_be_admin)

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
        logger.info("Синхронизация админов завершена (%s)", admin_ids)

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
        logger.info("Создана заявка на вывод %s для пользователя %s", request.id, user.id)
        return request

    @staticmethod
    @staticmethod
    async def get_statistics(session: AsyncSession):
        """Получить статистику по пользователям и карточкам."""
        stmt = (
            select(
                User.id,
                User.username,
                User.first_name,
                func.count(Card.id).label("total_cards"),
                # Вариант 1: Используем cast
                func.count(func.nullif(Card.is_approved, False)).label("approved_cards"),
                # Вариант 2: Или более простой способ
                func.sum(func.cast(Card.is_rejected, Integer)).label("rejected_cards"),
            )
            .join(Card, Card.user_id == User.id, isouter=True)
            .group_by(User.id)
            .order_by(User.id)
        )
        result = await session.execute(stmt)
        return result.all()
