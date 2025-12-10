import uuid
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

from src.database.models import Purchase, User, Card


class PaymentService:
    """Сервис для работы с платежами"""

    @staticmethod
    async def create_invoice(
            session: AsyncSession,
            user_id: int,
            card_id: int,
            amount: float
    ) -> Purchase:
        """Создание инвойса для покупки"""
        invoice_id = str(uuid.uuid4())

        purchase = Purchase(
            user_id=user_id,
            card_id=card_id,
            amount=amount,
            invoice_id=invoice_id,
            is_paid=False,
            created_at=datetime.utcnow()
        )

        session.add(purchase)
        await session.commit()
        await session.refresh(purchase)
        return purchase

    @staticmethod
    async def process_payment(
            session: AsyncSession,
            invoice_id: str
    ) -> bool:
        """Обработка платежа"""
        stmt = select(Purchase).where(
            Purchase.invoice_id == invoice_id,
            Purchase.is_paid == False
        )
        result = await session.execute(stmt)
        purchase = result.scalar_one_or_none()

        if purchase:
            # Обновляем баланс пользователя (продавца)
            stmt_user = select(User).where(User.id == purchase.card.user_id)
            result_user = await session.execute(stmt_user)
            seller = result_user.scalar_one()

            seller.balance += purchase.amount
            purchase.is_paid = True

            await session.commit()
            return True

        return False