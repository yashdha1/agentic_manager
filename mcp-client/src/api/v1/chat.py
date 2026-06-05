from fastapi import APIRouter, HTTPException

from src.api.v1.schemas import ChatRequest, ChatResponse, Message
from src.api.v1.threads import THREAD_MESSAGES
from src.declarative import graph as graph_module

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", responses={404: {"description": "Thread not found"}})
async def chat(request: ChatRequest) -> ChatResponse:
    if request.thread_id not in THREAD_MESSAGES:
        raise HTTPException(status_code=404, detail="Thread not found")

    THREAD_MESSAGES[request.thread_id].append(
        Message(role="user", content=request.message)
    )

    result = await graph_module.graph.ainvoke(
        {"messages": [{"role": "user", "content": request.message}]}
    )

    content = result["messages"][-1].content or "No response from assistant."

    THREAD_MESSAGES[request.thread_id].append(
        Message(role="assistant", content=content)
    )
    return ChatResponse(thread_id=request.thread_id, content=content)
