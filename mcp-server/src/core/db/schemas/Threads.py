from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from .base import Base


class Threads(Base):
    __tablename__ = "all_threads"

    id = Column(Integer, primary_key=True, index=True)
    thread_id = Column(String(255), unique=True, nullable=False, index=True)
    title = Column(String(500), nullable=False)
    created_at = Column(DateTime, nullable=False)
    ltm_saved = Column(Boolean, default=False, nullable=False)


class ThreadConversation(Base):
    __tablename__ = "thread_conversations"

    id = Column(Integer, primary_key=True, index=True)
    thread_id = Column(
        String(255),
        ForeignKey("all_threads.thread_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    ai_message = Column(Text, nullable=False)
    human_message = Column(Text, nullable=False)
    tool_calls = Column(Text, nullable=True)

    token_usage = Column(Integer, nullable=True)
    call_metadata = Column(Text, nullable=True)
    timestamp = Column(DateTime, nullable=False)
    thread = relationship("Threads", backref="conversations")
