from collections.abc import AsyncIterator
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, MetaData
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from supportdesk.config import get_settings


class Base(DeclarativeBase):
    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(table_name)s_%(column_0_name)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )


def now() -> datetime:
    return datetime.now(UTC)


class Identified:
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)


class Timestamped:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


engine = create_async_engine(
    get_settings().database_url, pool_pre_ping=True, hide_parameters=True
)
Session = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncIterator[AsyncSession]:
    async with Session() as session:
        yield session
