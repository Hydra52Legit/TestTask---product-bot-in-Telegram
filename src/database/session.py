from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.config import Config
from src.database.models import Base


def get_engine(config: Optional[Config] = None):
    """Create async engine based on configuration."""
    cfg = config or Config()
    return create_async_engine(cfg.database_url, echo=False, future=True)


def get_session_maker(engine=None) -> async_sessionmaker[AsyncSession]:
    """Return async session maker bound to provided engine."""
    eng = engine or get_engine()
    return async_sessionmaker(eng, expire_on_commit=False, class_=AsyncSession)


async def init_models(engine=None) -> None:
    """Create database tables if missing."""
    eng = engine or get_engine()
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
