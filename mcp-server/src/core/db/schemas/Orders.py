import enum

from sqlalchemy import ARRAY, Column, DateTime, Enum, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship

from .base import Base


class OrderStatus(enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    RETURNED = "returned"


class PaymentStatus(enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"
    PARTIALLY_REFUNDED = "partially_refunded"


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    status = Column(Enum(OrderStatus, name="order_status"), default=OrderStatus.PENDING)

    subtotal = Column(Numeric(10, 2), nullable=False)
    policy_applied = Column(ARRAY(String(100)), nullable=True)
    discount_amount = Column(Numeric(10, 2), nullable=False, default=0)
    shipping_amount = Column(Numeric(10, 2), nullable=False, default=0)

    currency = Column(String(3), nullable=True)
    payment_method = Column(String(50), nullable=True)
    payment_status = Column(
        Enum(PaymentStatus, name="payment_status"), nullable=False, default=PaymentStatus.PENDING
    )

    shipping_country = Column(String(100), nullable=True)
    shipping_city = Column(String(100), nullable=True)
    shipping_postcode = Column(String(20), nullable=True)
    device_type = Column(String(20), nullable=True)
    acquisition_channel = Column(String(50), nullable=True)

    ordered_at = Column(DateTime(timezone=True), nullable=False)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    refunds = relationship("Refund", back_populates="order")


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(
        Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id = Column(Integer, ForeignKey("products.id", ondelete="RESTRICT"), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    unit_price = Column(Numeric(10, 2), nullable=False)

    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")
