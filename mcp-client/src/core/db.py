"""SQLAlchemy async engine, session factory, and ORM models for mcp-client.

Mirrors the ``all_threads`` / ``thread_conversations`` tables owned by mcp-server.
"""

from __future__ import annotations

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, relationship

from src.core.config import settings


class Base(DeclarativeBase):
    pass


class Threads(Base):
    __tablename__ = "all_threads"

    id = Column(Integer, primary_key=True, index=True)
    thread_id = Column(String(255), unique=True, nullable=False, index=True)
    title = Column(String(500), nullable=False)
    created_at = Column(DateTime, nullable=False)
    ltm_saved = Column(Boolean, default=False, nullable=False)


class ThreadConversation(Base):
    __tablename__ = "thread_conversations"

    id = Column(Integer, primary_key=True, index=True)
    thread_id = Column(
        String(255),
        ForeignKey("all_threads.thread_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    human_message = Column(Text, nullable=False)
    ai_message = Column(Text, nullable=False)
    tool_calls = Column(Text, nullable=True)
    token_usage = Column(Integer, nullable=True)
    call_metadata = Column(Text, nullable=True)
    timestamp = Column(DateTime, nullable=False)

    thread = relationship("Threads", backref="conversations")


def _build_url() -> str:
    pw = settings.postgres_password
    return (
        f"postgresql+asyncpg://{settings.postgres_user}:{pw}"
        f"@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
    )


_engine = create_async_engine(_build_url(), pool_size=5, max_overflow=0)

AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=_engine,
    expire_on_commit=False,
)
