import asyncio
from uuid import uuid4

from fastapi import APIRouter, HTTPException

from src.api.v1 import state as api_state
from src.api.v1.schemas import (
    Message,
    ThreadDetailResponse,
    ThreadListItemResponse,
    ThreadResponse,
)
from src.core import chat_persistence

router = APIRouter(prefix="/threads", tags=["threads"])

# Keeps references to background tasks so they are not garbage-collected.
_bg_tasks: set[asyncio.Task] = set()


@router.get("")
async def list_threads() -> list[ThreadListItemResponse]:
    """Return all threads ordered most-recent first, with metadata."""
    try:
        threads_data = await chat_persistence.list_all_threads()
        return [
            ThreadListItemResponse(
                thread_id=t["thread_id"],
                title=t["title"],
                created_at=t["created_at"],
            )
            for t in threads_data
        ]
    except Exception:
        # Fallback: list from STM (in-memory, no metadata)
        thread_ids = await api_state.stm.list_threads()
        return [
            ThreadListItemResponse(
                thread_id=tid,
                title="Unnamed Thread",
                created_at=None,
            )
            for tid in thread_ids
        ]


@router.post("")
async def create_thread() -> ThreadResponse:
    thread_id = str(uuid4())
    await api_state.stm.create_thread(thread_id)
    try:
        await chat_persistence.ensure_thread(thread_id, "New Thread")
    except Exception:
        pass

    # Sweep all unsaved threads to LTM now that a new thread is being started.
    from src.core import ltm
    _t = asyncio.create_task(ltm.sweep_unsaved_threads(exclude_thread_id=thread_id))
    _bg_tasks.add(_t)
    _t.add_done_callback(_bg_tasks.discard)

    return ThreadResponse(thread_id=thread_id)


@router.get("/{thread_id}", responses={404: {"description": "Thread not found"}})
async def get_thread(thread_id: str) -> ThreadDetailResponse:
    """Return thread detail with full conversation history including tool calls.
    
    Priority:
    1. If STM has messages, use STM (live conversation).
    2. Fall back to PostgreSQL (persisted history).
    """
    # Try to fetch thread metadata first.
    thread_metadata = None
    try:
        threads_data = await chat_persistence.list_all_threads()
        thread_metadata = next((t for t in threads_data if t["thread_id"] == thread_id), None)
    except Exception:
        pass

    # Fast path: STM still alive (live conversation)
    if await api_state.stm.thread_exists(thread_id):
        msgs = await api_state.stm.get_messages(thread_id)
        messages = [
            Message(role=m["role"], content=m["content"])
            for m in msgs
        ]
        return ThreadDetailResponse(
            thread_id=thread_id,
            title=thread_metadata["title"] if thread_metadata else "Unnamed Thread",
            created_at=thread_metadata["created_at"] if thread_metadata else None,
            messages=messages,
        )

    # Fallback: read from PostgreSQL (STM expired or empty)
    try:
        conversations = await chat_persistence.get_conversations(thread_id)
        if conversations:
            messages = []
            for c in conversations:
                # Add user message
                messages.append(
                    Message(
                        role="user",
                        content=c["human_message"],
                        timestamp=c["timestamp"],
                    )
                )
                # Add assistant message with tool calls
                messages.append(
                    Message(
                        role="assistant",
                        content=c["ai_message"],
                        tool_calls=c["tool_calls"],
                        timestamp=c["timestamp"],
                    )
                )
            return ThreadDetailResponse(
                thread_id=thread_id,
                title=thread_metadata["title"] if thread_metadata else "Unnamed Thread",
                created_at=thread_metadata["created_at"] if thread_metadata else None,
                messages=messages,
            )
    except Exception:
        pass

    # Thread exists in metadata but has no persisted messages (e.g. new thread
    # created before any messages were sent, or STM was cleared after restart).
    if thread_metadata:
        return ThreadDetailResponse(
            thread_id=thread_id,
            title=thread_metadata["title"],
            created_at=thread_metadata["created_at"],
            messages=[],
        )

    raise HTTPException(status_code=404, detail="Thread not found")

