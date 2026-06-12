import asyncio
from uuid import uuid4

from fastapi import APIRouter, HTTPException

from src.api.v1 import state as api_state
from src.api.v1.schemas import Message, ThreadDetailResponse, ThreadResponse
from src.core import chat_persistence

router = APIRouter(prefix="/threads", tags=["threads"])

# Keeps references to background tasks so they are not garbage-collected.
_bg_tasks: set[asyncio.Task] = set()


@router.get("")
async def list_threads() -> list[ThreadResponse]:
    try:
        thread_ids = await chat_persistence.list_all_threads()
    except Exception:
        thread_ids = await api_state.stm.list_threads()
    return [ThreadResponse(thread_id=t) for t in thread_ids]


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
    # Fast path: STM still alive
    if await api_state.stm.thread_exists(thread_id):
        msgs = await api_state.stm.get_messages(thread_id)
        return ThreadDetailResponse(
            thread_id=thread_id,
            messages=[Message(role=m["role"], content=m["content"]) for m in msgs],
        )

    # Fallback: read from PostgreSQL (STM expired or empty)
    try:
        conversations = await chat_persistence.get_conversations(thread_id)
        if conversations:
            messages = []
            for c in conversations:
                messages.append(Message(role="user", content=c["human_message"]))
                messages.append(Message(role="assistant", content=c["ai_message"]))
            return ThreadDetailResponse(thread_id=thread_id, messages=messages)
    except Exception:
        pass

    raise HTTPException(status_code=404, detail="Thread not found")

