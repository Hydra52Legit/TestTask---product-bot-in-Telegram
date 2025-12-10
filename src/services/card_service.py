from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime

from src.database.models import Card, User


class CardService:
    """Сервис для работы с карточками"""

    @staticmethod
    async def create_card(
            session: AsyncSession,
            user_id: int,
            title: str,
            description: str,
            price: float,
            photo_url: Optional[str] = None
    ) -> Card:
        """Создание новой карточки"""
        card = Card(
            title=title,
            description=description,
            price=price,
            photo_url=photo_url,
            user_id=user_id,
            is_approved=False,
            created_at=datetime.utcnow()
        )
        session.add(card)
        await session.commit()
        await session.refresh(card)
        return card

    @staticmethod
    async def get_approved_cards(
            session: AsyncSession,
            limit: int = 50,
            offset: int = 0
    ) -> List[Card]:
        """Получение одобренных карточек"""
        stmt = select(Card).where(
            Card.is_approved == True
        ).order_by(
            Card.created_at.desc()
        ).offset(offset).limit(limit)

        result = await session.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def get_cards_for_moderation(
            session: AsyncSession
    ) -> List[Card]:
        """Получение карточек на модерацию"""
        stmt = select(Card).where(
            Card.is_approved == False,
            Card.is_rejected == False
        ).order_by(Card.created_at.asc())

        result = await session.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def approve_card(
            session: AsyncSession,
            card_id: int
    ) -> bool:
        """Одобрение карточки"""
        stmt = select(Card).where(Card.id == card_id)
        result = await session.execute(stmt)
        card = result.scalar_one_or_none()

        if card:
            card.is_approved = True
            await session.commit()
            return True
        return False