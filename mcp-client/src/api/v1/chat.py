from fastapi import APIRouter

from src.api.v1.schemas import ChatRequest, ChatResponse
from src.declarative import workflow as workflow_module

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("")
async def chat(request: ChatRequest) -> ChatResponse:
    result = await workflow_module.graph.ainvoke({"query": request.message})
    return ChatResponse(
        response=result["final_response"],
        thread_id=request.thread_id,
    )
