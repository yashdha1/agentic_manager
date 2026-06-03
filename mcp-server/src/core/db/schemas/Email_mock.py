from sqlalchemy import ARRAY, Boolean, Column, DateTime, Integer, String, Text

from .base import Base


class Email(Base):
    __tablename__ = "emails"

    id = Column(Integer, primary_key=True, index=True)

    message_id = Column(String(255), unique=True, nullable=False, index=True)
    recipients = Column(ARRAY(String(255)), nullable=False, index=True)

    bcc = Column(Text, nullable=True)

    subject = Column(String(500), nullable=True)
    body = Column(Text, nullable=True)
    html_body = Column(Text, nullable=True)

    status = Column(String(50), nullable=False, default="received")
    is_read = Column(Boolean, nullable=False, default=False)

    received_at = Column(DateTime(timezone=True), nullable=False)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=True)