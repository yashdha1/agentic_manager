from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from .base import Base


class InventoryEvent(Base):
    __tablename__ = "inventory_events"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(
        Integer, ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    event_type = Column(String(30), nullable=False)  # sale_deduction / restock / adjustment
    quantity_change = Column(Integer, nullable=False)
    new_stock_level = Column(Integer, nullable=False)
    event_date = Column(DateTime(timezone=True), nullable=False)
    notes = Column(Text, nullable=True)

    product = relationship("Product", backref="inventory_events")
