from datetime import datetime

from pydantic import BaseModel


class Message(BaseModel):
    role: str
    content: str
    tool_calls: str | None = None  # JSON string of tool calls
    timestamp: datetime | None = None


class ChatRequest(BaseModel):
    message: str
    thread_id: str | None = None


class ChatResponse(BaseModel):
    response: str
    thread_id: str | None = None


class StreamChatRequest(BaseModel):
    message: str
    thread_id: str | None = None


class ResumeChatRequest(BaseModel):
    thread_id: str
    decisions: list[dict]


class ThreadResponse(BaseModel):
    thread_id: str


class ThreadListItemResponse(BaseModel):
    """Thread metadata for list view."""
    thread_id: str
    title: str
    created_at: datetime | None = None


class ThreadDetailResponse(BaseModel):
    thread_id: str
    title: str
    created_at: datetime | None = None
    messages: list[Message]
