"""Helpers for persisting chat turns to PostgreSQL.

Writes to the ``all_threads`` and ``thread_conversations`` tables that are
defined (and schema-created) by mcp-server on startup.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select, update

from src.core.db import AsyncSessionLocal, ThreadConversation, Threads


async def ensure_thread(thread_id: str, title: str) -> None:
    """Insert a thread row — silently ignores duplicates."""
    async with AsyncSessionLocal() as session:
        existing = await session.scalar(
            select(Threads).where(Threads.thread_id == thread_id)
        )
        if existing is None:
            session.add(
                Threads(
                    thread_id=thread_id,
                    title=title,
                    created_at=datetime.now(UTC).replace(tzinfo=None),
                    ltm_saved=False,
                )
            )
            await session.commit()


async def save_conversation(
    thread_id: str,
    human_msg: str,
    ai_msg: str,
    tool_calls: str | None = None,
    token_usage: int | None = None,
) -> None:
    """Append one user/assistant turn to ``thread_conversations``."""
    async with AsyncSessionLocal() as session:
        session.add(
            ThreadConversation(
                thread_id=thread_id,
                human_message=human_msg,
                ai_message=ai_msg,
                tool_calls=tool_calls,
                token_usage=token_usage,
                call_metadata=None,
                timestamp=datetime.now(UTC).replace(tzinfo=None),
            )
        )
        await session.commit()


async def get_conversations(thread_id: str) -> list[dict]:
    """Return all turns for *thread_id* ordered oldest-first, including tool calls."""
    async with AsyncSessionLocal() as session:
        rows = (
            await session.scalars(
                select(ThreadConversation)
                .where(ThreadConversation.thread_id == thread_id)
                .order_by(ThreadConversation.timestamp.asc())
            )
        ).all()
    return [
        {
            "human_message": r.human_message,
            "ai_message": r.ai_message,
            "tool_calls": r.tool_calls,
            "timestamp": r.timestamp,
        }
        for r in rows
    ]


async def list_all_threads() -> list[dict]:
    """Return all threads ordered most-recent first, with metadata."""
    async with AsyncSessionLocal() as session:
        rows = (
            await session.scalars(
                select(Threads).order_by(Threads.created_at.desc())
            )
        ).all()
    return [
        {
            "thread_id": r.thread_id,
            "title": r.title,
            "created_at": r.created_at,
        }
        for r in rows
    ]


async def mark_ltm_saved(thread_id: str) -> None:
    async with AsyncSessionLocal() as session:
        await session.execute(
            update(Threads)
            .where(Threads.thread_id == thread_id)
            .values(ltm_saved=True)
        )
        await session.commit()


async def get_unsaved_thread_ids() -> list[str]:
    """Return thread_ids that have not yet been saved to LTM."""
    async with AsyncSessionLocal() as session:
        rows = (
            await session.scalars(
                select(Threads).where(not Threads.ltm_saved)
            )
        ).all()
    return [r.thread_id for r in rows]
