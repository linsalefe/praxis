"""Engine e sessão SQLAlchemy async."""
from collections.abc import AsyncIterator
from contextvars import ContextVar

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

_settings = get_settings()

engine = create_async_engine(
    _settings.database_url,
    echo=_settings.env == "dev" and False,  # ligue manualmente para debug
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


class Base(DeclarativeBase):
    pass


# Contexto do request para middleware de audit e tenant.
current_user_id: ContextVar[str | None] = ContextVar("current_user_id", default=None)
current_tenant_id: ContextVar[str | None] = ContextVar("current_tenant_id", default=None)
current_request_ip: ContextVar[str | None] = ContextVar("current_request_ip", default=None)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
