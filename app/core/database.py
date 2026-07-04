import contextlib
from collections.abc import AsyncGenerator, AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import exc as sa_exc
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


class Base(DeclarativeBase):
    pass


engine: AsyncEngine | None = None
async_session_maker: async_sessionmaker[AsyncSession] | None = None


def init_engine(*, echo: bool | None = None) -> None:
    global async_session_maker, engine

    if engine is not None:
        return

    engine = create_async_engine(
        settings.DATABASE_URL.unicode_string(),
        echo=settings.SQL_ECHO if echo is None else echo,
        pool_pre_ping=True,
    )
    async_session_maker = async_sessionmaker(
        bind=engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )


async def dispose_engine() -> None:
    global async_session_maker, engine

    if engine is not None:
        await engine.dispose()

    engine = None
    async_session_maker = None


@asynccontextmanager
async def session_context() -> AsyncIterator[AsyncSession]:
    if async_session_maker is None:
        init_engine()

    if async_session_maker is None:
        raise RuntimeError("Engine is not initialized.")

    async with async_session_maker() as session:
        async with session.begin():
            try:
                yield session
            except Exception:
                with contextlib.suppress(sa_exc.InvalidRequestError):
                    await session.rollback()
                raise


async def check_database() -> None:
    if engine is None:
        init_engine()

    if engine is None:
        raise RuntimeError("Engine is not initialized.")

    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))


async def close_database() -> None:
    await dispose_engine()
