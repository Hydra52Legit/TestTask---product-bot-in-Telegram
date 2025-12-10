import pytest

from src.database.models import Card, User
from src.services.payment_service import PaymentService


@pytest.mark.asyncio
async def test_payment_process_updates_balance(session):
    seller = User(telegram_id=2, username="seller")
    buyer = User(telegram_id=3, username="buyer")
    session.add_all([seller, buyer])
    await session.commit()
    await session.refresh(seller)
    await session.refresh(buyer)

    card = Card(
        title="Test card",
        description="Desc",
        price=15.0,
        user_id=seller.id,
        is_approved=True,
    )
    session.add(card)
    await session.commit()
    await session.refresh(card)

    purchase = await PaymentService.create_invoice(
        session=session, user_id=buyer.id, card_id=card.id, amount=card.price
    )

    processed = await PaymentService.process_payment(session, purchase.invoice_id)
    assert processed is True

    await session.refresh(seller)
    await session.refresh(purchase)
    assert purchase.is_paid is True
    assert seller.balance == pytest.approx(card.price)

