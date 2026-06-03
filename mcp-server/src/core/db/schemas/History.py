import enum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    Text,
)
from sqlalchemy.orm import relationship

from .base import Base


class RefundStatus(enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    PROCESSED = "processed"


class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    order_id = Column(
        Integer, ForeignKey("orders.id", ondelete="SET NULL"), nullable=True, index=True
    )
    product_id = Column(
        Integer, ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    rating = Column(SmallInteger, nullable=False)  # 1–5
    title = Column(Text, nullable=True)
    body = Column(Text, nullable=True)
    verified_purchase = Column(Boolean, nullable=False, default=False)
    helpful_votes = Column(Integer, nullable=False, default=0)
    flagged = Column(Boolean, nullable=False, default=False)

    reviewed_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="reviews")
    order = relationship("Order", foreign_keys=[order_id])
    product = relationship("Product", back_populates="reviews")


class Refund(Base):
    __tablename__ = "refunds"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(
        Integer, ForeignKey("orders.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    refund_amount = Column(Numeric(10, 2), nullable=False)
    reason = Column(Text, nullable=False)
    status = Column(
        Enum(RefundStatus, name="refund_status"), nullable=False, default=RefundStatus.PENDING
    )

    processed_at = Column(DateTime(timezone=True), nullable=True)

    order = relationship("Order", back_populates="refunds")
