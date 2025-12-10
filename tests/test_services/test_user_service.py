import pytest

from src.database.models import User
from src.services.user_service import UserService


@pytest.mark.asyncio
async def test_get_or_create_sets_admin(session):
    admin_ids = [123]
    user = await UserService.get_or_create(
        session=session,
        telegram_id=123,
        username="admin",
        first_name="Admin",
        last_name=None,
        admin_ids=admin_ids,
    )
    assert user.is_admin is True


@pytest.mark.asyncio
async def test_create_withdrawal_request_validations(session):
    user = User(telegram_id=50, balance=200.0)
    session.add(user)
    await session.commit()
    await session.refresh(user)

    request = await UserService.create_withdrawal_request(
        session=session,
        user=user,
        amount=150.0,
        requisites="card 123",
        min_amount=100.0,
    )
    assert request.id is not None

    with pytest.raises(ValueError):
        await UserService.create_withdrawal_request(
            session=session,
            user=user,
            amount=50.0,
            requisites="card 123",
            min_amount=100.0,
        )

