"""Long-Term Memory: summarise an expired STM thread and store it in Qdrant."""

from __future__ import annotations

from datetime import UTC, datetime

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import AzureChatOpenAI

from src.core.chat_persistence import get_conversations, mark_ltm_saved
from src.core.config import settings
from src.core.logger import logger
from src.core.qdrant import upsert_ltm

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
            api_key=settings.azure_api_key.get_secret_value() if settings.azure_api_key else None,
            api_version=settings.azure_api_version,
        )
        response = await llm.ainvoke(
            [SystemMessage(content=_SUMMARISE_PROMPT), HumanMessage(content=transcript)]
        )
        summary: str = response.content if isinstance(response.content, str) else str(response.content)

        await upsert_ltm(
            thread_id=thread_id,
            summary=summary,
            metadata={"timestamp": datetime.now(UTC).isoformat()},
        )
        await mark_ltm_saved(thread_id)
        logger.info("LTM saved for thread {}.", thread_id)

    except Exception as exc:
        logger.error("LTM generation failed for thread {}: {}", thread_id, exc)
