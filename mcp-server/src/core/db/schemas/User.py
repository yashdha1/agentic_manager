from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.orm import relationship

from .base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    phone = Column(String(20), nullable=True)
    country = Column(String(100), nullable=True)
    city = Column(String(100), nullable=True)
    postcode = Column(String(20), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    customer_tier = Column(String(20), nullable=True)
    has_newsletter = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=True)

    orders = relationship("Order", back_populates="user")
    reviews = relationship("Review", back_populates="user")
