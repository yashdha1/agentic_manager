"""Qdrant client for mcp-client (Long-Term Memory writes)."""

from __future__ import annotations

import uuid
from functools import lru_cache

from langchain_openai import AzureOpenAIEmbeddings
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

from src.core.config import settings


@lru_cache(maxsize=1)
def _qdrant() -> QdrantClient:
    return QdrantClient(url=f"{settings.qdrant_host}:{settings.qdrant_port}")


@lru_cache(maxsize=1)
def _embeddings() -> AzureOpenAIEmbeddings:
    return AzureOpenAIEmbeddings(
        azure_deployment=settings.azure_embedding_model,
        azure_endpoint=settings.azure_endpoint,
        api_key=settings.azure_api_key.get_secret_value() if settings.azure_api_key else None,
        api_version=settings.azure_api_version,
        dimensions=settings.azure_embedding_dimensions,
    )


async def upsert_ltm(thread_id: str, summary: str, metadata: dict) -> None:
    """Embed *summary* and upsert into the thread LTM collection."""
    vector = await _embeddings().aembed_query(summary)
    _qdrant().upsert(
        collection_name=settings.qdrant_thread_collection,
        points=[
            PointStruct(
                id=str(uuid.uuid5(uuid.NAMESPACE_DNS, thread_id)),
                vector=vector,
                payload={"thread_id": thread_id, "summary": summary, **metadata},
            )
        ],
    )


async def upsert_resolver(
    thread_id: str,
    tool_name: str,
    original_args: dict,
    decisions: list,
    timestamp: str,
) -> None:
    """Embed a HITL resolution record and upsert into the resolver_memory collection."""
    text = (
        f"HITL Resolution — Tool: {tool_name} | "
        f"Args: {original_args} | "
        f"Decision: {decisions} | "
        f"Thread: {thread_id}"
    )
    vector = await _embeddings().aembed_query(text)
    _qdrant().upsert(
        collection_name=settings.qdrant_resolver_collection,
        points=[
            PointStruct(
                id=str(uuid.uuid4()),
                vector=vector,
                payload={
                    "thread_id": thread_id,
                    "tool_name": tool_name,
                    "original_args": original_args,
                    "decisions": decisions,
                    "timestamp": timestamp,
                },
            )
        ],
    )
