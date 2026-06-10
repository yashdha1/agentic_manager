from uuid import uuid4

from fastapi import APIRouter, HTTPException

from src.api.v1.schemas import Message, ThreadDetailResponse, ThreadResponse
from src.api.v1 import state as api_state

router = APIRouter(prefix="/threads", tags=["threads"])


@router.get("")
async def list_threads() -> list[ThreadResponse]:
    thread_ids = await api_state.stm.list_threads()
    return [ThreadResponse(thread_id=t) for t in thread_ids]


@router.post("")
async def create_thread() -> ThreadResponse:
    thread_id = str(uuid4())
    await api_state.stm.create_thread(thread_id)
    return ThreadResponse(thread_id=thread_id)


@router.get("/{thread_id}", responses={404: {"description": "Thread not found"}})
async def get_thread(thread_id: str) -> ThreadDetailResponse:
    if not await api_state.stm.thread_exists(thread_id):
        raise HTTPException(status_code=404, detail="Thread not found")
    messages = [
        Message(role=m["role"], content=m["content"])
        for m in await api_state.stm.get_messages(thread_id)
    ]
    return ThreadDetailResponse(thread_id=thread_id, messages=messages)

