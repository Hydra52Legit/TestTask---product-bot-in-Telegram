import pytest

from src.database.models import Card, User
from src.services.card_service import CardService


@pytest.mark.asyncio
async def test_create_and_approve_card(session):
    user = User(telegram_id=1, username="testuser")
    session.add(user)
    await session.commit()
    await session.refresh(user)

    card = await CardService.create_card(
        session=session,
        user_id=user.id,
        title="Test",
        description="Desc",
        price=10.0,
        photo_url=None,
    )

    assert card.id is not None
    assert card.is_approved is False

    await CardService.approve_card(session, card.id)
    updated = await session.get(Card, card.id)
    assert updated.is_approved is True


@pytest.mark.asyncio
async def test_update_card_attribute(session):
    user = User(telegram_id=2, username="editor")
    session.add(user)
    await session.commit()
    await session.refresh(user)

    card = await CardService.create_card(
        session=session,
        user_id=user.id,
        title="Old",
        description="Old desc",
        price=5.0,
    )

    updated = await CardService.update_card_attribute(
        session=session, card_id=card.id, attribute="price", value="12.5"
    )
    refreshed = await session.get(Card, card.id)
    assert updated is True
    assert refreshed.price == pytest.approx(12.5)

