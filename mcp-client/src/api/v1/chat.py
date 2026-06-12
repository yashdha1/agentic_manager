import asyncio
import json
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage
from langgraph.types import Command

from src.api.v1 import state as api_state
from src.api.v1.schemas import ChatRequest, ChatResponse, ResumeChatRequest, StreamChatRequest
from src.declarative import workflow as workflow_module

router = APIRouter(prefix="/chat", tags=["chat"])

AGENT_NODES = {"orchestrator", "sales", "customers", "inventory", "knowledge", "aggregator"}

# Background tasks — keeps references so they are not garbage-collected.
_bg_tasks: set[asyncio.Task] = set()


def _fire(coro) -> None:
    """Schedule *coro* as a tracked background task."""
    t = asyncio.create_task(coro)
    _bg_tasks.add(t)
    t.add_done_callback(_bg_tasks.discard)

@router.post("")
async def chat(request: ChatRequest) -> ChatResponse:
    thread_id = request.thread_id or str(uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    result = await workflow_module.graph.ainvoke(
        {"query": request.message, "thread_id": thread_id, "messages": [HumanMessage(content=request.message)]},
        config,
    )
    return ChatResponse(response=result.get("final_response", ""), thread_id=thread_id)


async def _sse_events(input_data, config: dict, thread_id: str, user_message: str | None):
    """Shared SSE generator for /stream and /resume endpoints."""
    total_usage: dict[str, int] = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}

    async for event in workflow_module.graph.astream_events(input_data, config, version="v2"):
        kind: str = event["event"]
        name: str = event.get("name", "")
        node: str = event.get("metadata", {}).get("langgraph_node", "")

        if kind == "on_chain_start" and name in AGENT_NODES:
            yield f"data: {json.dumps({'type': 'agent_start', 'agent': name})}\n\n"

        elif kind == "on_chain_end" and name in AGENT_NODES:
            yield f"data: {json.dumps({'type': 'agent_end', 'agent': name})}\n\n"

        elif kind == "on_chat_model_stream":
            chunk = event["data"]["chunk"]
            content = chunk.content
            if isinstance(content, list):
                text = "".join(c.get("text", "") for c in content if isinstance(c, dict))
            else:
                text = content or ""
            if text:
                yield f"data: {json.dumps({'type': 'token', 'agent': node, 'content': text})}\n\n"

        elif kind == "on_tool_start" and node in AGENT_NODES:
            yield f"data: {json.dumps({'type': 'tool_call', 'agent': node, 'tool': name})}\n\n"

        elif kind == "on_chat_model_end":
            output = event.get("data", {}).get("output")
            if output and hasattr(output, "usage_metadata") and output.usage_metadata:
                um = output.usage_metadata
                total_usage["input_tokens"] += um.get("input_tokens", 0)
                total_usage["output_tokens"] += um.get("output_tokens", 0)
                total_usage["total_tokens"] += um.get("total_tokens", 0)

    # After stream exhausts — check if graph is paused (interrupted) or done
    snap = await workflow_module.graph.aget_state(config)

    if snap.next:  # graph is paused at human_approval
        interrupt_val: dict = {}
        for task in snap.tasks:
            if task.interrupts:
                interrupt_val = task.interrupts[0].value
                break
        # Persist user message now (before user decides)
        if user_message is not None:
            await api_state.stm.append_message(thread_id, "user", user_message)
        yield f"data: {json.dumps({'type': 'interrupt', 'data': interrupt_val}, default=str)}\n\n"
    else:
        final_response = snap.values.get("final_response", "")
        if user_message is not None:
            await api_state.stm.append_message(thread_id, "user", user_message)
        await api_state.stm.append_message(thread_id, "assistant", final_response)
        yield f"data: {json.dumps({'type': 'token_usage', 'data': total_usage})}\n\n"
        yield f"data: {json.dumps({'type': 'done', 'final_response': final_response})}\n\n"


@router.post("/stream")
async def stream_chat(request: StreamChatRequest):
    thread_id = request.thread_id or str(uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    async def generator():
        yield f"data: {json.dumps({'type': 'thread_id', 'data': thread_id})}\n\n"
        async for chunk in _sse_events(
            {"query": request.message, "thread_id": thread_id, "messages": [HumanMessage(content=request.message)]},
            config,
            thread_id,
            request.message,
        ):
            yield chunk

    return StreamingResponse(generator(), media_type="text/event-stream")


@router.post("/resume")
async def resume_chat(request: ResumeChatRequest):
    config = {"configurable": {"thread_id": request.thread_id}}
    resume_value = {"decisions": request.decisions}

    # Capture interrupted tool info BEFORE resuming so we can save it to
    # resolver_memory after the tool executes.
    snap_before = await workflow_module.graph.aget_state(config)
    interrupt_info: dict = {}
    for task in snap_before.tasks:
        if task.interrupts:
            hitl_req = task.interrupts[0].value
            action_requests = hitl_req.get("action_requests", [])
            if action_requests:
                interrupt_info = {
                    "tool_name": action_requests[0].get("name", ""),
                    "original_args": action_requests[0].get("args", {}),
                }
            break

    async def generator():
        async for chunk in _sse_events(Command(resume=resume_value), config, request.thread_id, None):
            yield chunk
        # After stream completes — if we had interrupt info, save resolution to Qdrant.
        if interrupt_info:
            from src.core.qdrant import upsert_resolver
            _fire(upsert_resolver(
                thread_id=request.thread_id,
                tool_name=interrupt_info["tool_name"],
                original_args=interrupt_info["original_args"],
                decisions=request.decisions,
                timestamp=datetime.now(UTC).isoformat(),
            ))

    return StreamingResponse(generator(), media_type="text/event-stream")
