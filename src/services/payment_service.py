import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.database.models import Card, Purchase, User


class PaymentService:
    """Сервис для работы с платежами."""

    @staticmethod
    async def create_invoice(
        session: AsyncSession, user_id: int, card_id: int, amount: float
    ) -> Purchase:
        invoice_id = str(uuid.uuid4())
        purchase = Purchase(
            user_id=user_id,
            card_id=card_id,
            amount=amount,
            invoice_id=invoice_id,
            is_paid=False,
            created_at=datetime.utcnow(),
        )
        session.add(purchase)
        await session.commit()
        await session.refresh(purchase)
        return purchase

    @staticmethod
    async def process_payment(session: AsyncSession, invoice_id: str) -> bool:
        stmt = (
            select(Purchase)
            .options(selectinload(Purchase.card))
            .where(Purchase.invoice_id == invoice_id, Purchase.is_paid.is_(False))
        )
        purchase = (await session.execute(stmt)).scalar_one_or_none()
        if not purchase:
            return False

        card = purchase.card
        if not card:
            return False

        seller_stmt = select(User).where(User.id == card.user_id)
        seller = (await session.execute(seller_stmt)).scalar_one_or_none()
        if not seller:
            return False

        seller.balance += purchase.amount
        purchase.is_paid = True
        await session.commit()
        return True