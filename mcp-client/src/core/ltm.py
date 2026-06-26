"""Long-Term Memory: summarise an expired STM thread and store it in Qdrant."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import AzureChatOpenAI

from src.core.chat_persistence import get_conversations, mark_ltm_saved
from src.core.config import settings
from src.core.logger import logger
from src.core.qdrant import upsert_ltm

# Keeps references to background tasks so they are not garbage-collected.
_bg_tasks: set[asyncio.Task] = set()

_SUMMARISE_PROMPT = (
    "Summarise the following customer-support conversation in one concise paragraph. "
    "Capture key topics, decisions, and outcomes."
)


async def process_thread_expiry(thread_id: str) -> None:
    """Called when Redis STM key for *thread_id* expires.

    1. Fetches the full conversation from PostgreSQL.
    2. Generates an LLM summary.
    3. Upserts the summary vector into Qdrant ``thread_collection``.
    4. Marks the thread as LTM-saved in PostgreSQL.
    """
    try:
        conversations = await get_conversations(thread_id)
        if not conversations:
            logger.info("STM expired for thread {} — no PG history, skipping LTM.", thread_id)
            return

        transcript = "\n".join(
            f"User: {c['human_message']}\nAssistant: {c['ai_message']}"
            for c in conversations
        )

        llm = AzureChatOpenAI(
            azure_deployment=settings.azure_chat_light_model,
            azure_endpoint=settings.azure_endpoint,
            api_key=settings.azure_api_key.get_secret_value(),
            api_version=settings.azure_api_version,
        )
        response = await llm.ainvoke(
            [SystemMessage(content=_SUMMARISE_PROMPT), HumanMessage(content=transcript)]
        )
        summary: str = (
            response.content
            if isinstance(response.content, str)
            else str(response.content)
        )

        await upsert_ltm(
            thread_id=thread_id,
            summary=summary,
            metadata={"timestamp": datetime.now(UTC).isoformat()},
        )
        await mark_ltm_saved(thread_id)
        logger.info("LTM saved for thread {}.", thread_id)

    except Exception as exc:
        logger.error("LTM generation failed for thread {}: {}", thread_id, exc)


async def sweep_unsaved_threads(exclude_thread_id: str | None = None) -> None:
    """Fire LTM processing for all threads not yet saved to LTM.

    Called when a new thread is created so prior conversations are persisted
    before they expire naturally.  Each thread is processed as a separate
    asyncio task to avoid blocking the request.

    Args:
        stm: The STM instance (RedisSTM or InMemorySTM) — unused directly but
             kept for potential future use (e.g. checking if key still exists).
        exclude_thread_id: Skip this thread_id (the newly created thread which
                           has no messages yet).
    """
    from src.core.chat_persistence import get_unsaved_thread_ids

    try:
        thread_ids = await get_unsaved_thread_ids()
        for tid in thread_ids:
            if tid == exclude_thread_id:
                continue
            task = asyncio.create_task(process_thread_expiry(tid))
            _bg_tasks.add(task)
            task.add_done_callback(_bg_tasks.discard)
            logger.info("Queued LTM sweep for thread {}.", tid)
            
    except Exception as exc:
        logger.error("LTM sweep failed: {}", exc)
