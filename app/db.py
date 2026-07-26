"""Database engine, session factory, and health helpers."""

from collections.abc import AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.models import Base

settings = get_settings()
engine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)
SessionFactory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncIterator[AsyncSession]:
    """Yield one request-scoped database session."""
    async with SessionFactory() as session:
        yield session


async def create_schema() -> None:
    """Create tables for local development; production should use Alembic."""
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


async def check_database() -> bool:
    """Return whether the database accepts a trivial query."""
    try:
        async with SessionFactory() as session:
            await session.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
