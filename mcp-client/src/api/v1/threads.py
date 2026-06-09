from uuid import uuid4

from fastapi import APIRouter, HTTPException

from src.api.v1.schemas import Message, ThreadDetailResponse, ThreadResponse
from src.api.v1.state import THREAD_MESSAGES

router = APIRouter(prefix="/threads", tags=["threads"])


@router.get("")
async def list_threads() -> list[ThreadResponse]:
    return [ThreadResponse(thread_id=t) for t in THREAD_MESSAGES.keys()]


@router.post("")
async def create_thread() -> ThreadResponse:
    thread_id = str(uuid4())
    THREAD_MESSAGES.setdefault(thread_id, [])
    return ThreadResponse(thread_id=thread_id)


@router.get("/{thread_id}", responses={404: {"description": "Thread not found"}})
async def get_thread(thread_id: str) -> ThreadDetailResponse:
    if thread_id not in THREAD_MESSAGES:
        raise HTTPException(status_code=404, detail="Thread not found")
    messages = [Message(role=m["role"], content=m["content"]) for m in THREAD_MESSAGES[thread_id]]
    return ThreadDetailResponse(thread_id=thread_id, messages=messages)

