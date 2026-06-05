from collections.abc import MutableMapping

from fastapi import APIRouter, HTTPException
from langgraph_sdk import get_client

from src.api.v1.schemas import Message, ThreadDetailResponse, ThreadResponse
from src.core.config import settings

router = APIRouter(prefix="/threads", tags=["threads"])

# Minimal in-memory store for chat UI thread switching.
THREAD_MESSAGES: MutableMapping[str, list[Message]] = {}


@router.get("")
async def list_threads() -> list[ThreadResponse]:
    return [ThreadResponse(thread_id=thread_id) for thread_id in THREAD_MESSAGES.keys()]


@router.post("")
async def create_thread() -> ThreadResponse:
    client = get_client(url=settings.langgraph_api_url)
    thread = await client.threads.create()
    thread_id = thread["thread_id"]
    THREAD_MESSAGES.setdefault(thread_id, [])
    return ThreadResponse(thread_id=thread_id)


@router.get("/{thread_id}", responses={404: {"description": "Thread not found"}})
async def get_thread(thread_id: str) -> ThreadDetailResponse:
    if thread_id not in THREAD_MESSAGES:
        raise HTTPException(status_code=404, detail="Thread not found")
    return ThreadDetailResponse(thread_id=thread_id, messages=THREAD_MESSAGES[thread_id])

