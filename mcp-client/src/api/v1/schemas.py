from pydantic import BaseModel


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    thread_id: str
    message: str


class ChatResponse(BaseModel):
    thread_id: str
    content: str


class ThreadResponse(BaseModel):
    thread_id: str


class ThreadDetailResponse(BaseModel):
    thread_id: str
    messages: list[Message]
