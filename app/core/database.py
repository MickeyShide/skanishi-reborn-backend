from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


class Base(DeclarativeBase):
    pass


engine = create_async_engine(
    settings.DATABASE_URL.unicode_string(),
    echo=settings.SQL_ECHO,
    pool_pre_ping=True,
)

async_session_maker = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


async def get_session() -> AsyncGenerator[AsyncSession]:
    async with async_session_maker() as session:
        yield session


async def check_database() -> None:
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))


async def close_database() -> None:
    await engine.dispose()
