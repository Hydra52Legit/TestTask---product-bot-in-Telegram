from datetime import datetime
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.database.models import Card


class CardService:
    """Сервис для работы с карточками."""

    @staticmethod
    async def create_card(
        session: AsyncSession,
        user_id: int,
        title: str,
        description: str,
        price: float,
        photo_url: Optional[str] = None,
        photo_file_id: Optional[str] = None,
    ) -> Card:
        card = Card(
            title=title,
            description=description,
            price=price,
            photo_url=photo_url,
            photo_file_id=photo_file_id,
            user_id=user_id,
            is_approved=False,
            created_at=datetime.utcnow(),
        )
        session.add(card)
        await session.commit()
        await session.refresh(card)
        return card

    @staticmethod
    async def get_approved_cards(
        session: AsyncSession, limit: int = 50, offset: int = 0
    ) -> List[Card]:
        stmt = (
            select(Card)
            .where(Card.is_approved.is_(True))
            .order_by(Card.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await session.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def get_cards_for_moderation(session: AsyncSession) -> List[Card]:
        stmt = (
            select(Card)
            .options(selectinload(Card.user))
            .where(Card.is_approved.is_(False), Card.is_rejected.is_(False))
            .order_by(Card.created_at.asc())
        )
        result = await session.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def approve_card(session: AsyncSession, card_id: int) -> bool:
        card = await CardService.get_card_by_id(session, card_id)
        if card:
            card.is_approved = True
            card.is_rejected = False
            await session.commit()
            return True
        return False

    @staticmethod
    async def reject_card(session: AsyncSession, card_id: int) -> bool:
        card = await CardService.get_card_by_id(session, card_id)
        if card:
            card.is_rejected = True
            await session.commit()
            return True
        return False

    @staticmethod
    async def update_card_attribute(
        session: AsyncSession, card_id: int, attribute: str, value: str
    ) -> bool:
        card = await CardService.get_card_by_id(session, card_id)
        if not card:
            return False

        if attribute == "title":
            card.title = value
        elif attribute == "description":
            card.description = value
        elif attribute == "price":
            try:
                card.price = float(value)
            except ValueError:
                return False
        elif attribute == "photo_url":
            card.photo_url = value
        else:
            return False

        await session.commit()
        return True

    @staticmethod
    async def get_card_by_id(session: AsyncSession, card_id: int) -> Optional[Card]:
        stmt = select(Card).options(selectinload(Card.user)).where(Card.id == card_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()