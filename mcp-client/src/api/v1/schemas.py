from pydantic import BaseModel


class Message(BaseModel):
    role: str
    content: str


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


class ThreadDetailResponse(BaseModel):
    thread_id: str
    messages: list[Message]
