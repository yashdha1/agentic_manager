from core.db.schemas import InventoryEvent, Product

from tools.sales_tools.helpers import _as_float


def _product_payload(p: Product) -> dict:
	return {
		"product_id": p.id,
		"sku": p.sku,
		"name": p.name,
		"category": p.category,
		"sub_category": p.sub_category,
		"brand": p.brand,
		"stock_quantity": p.stock_quantity,
		"price": _as_float(p.price),
		"is_active": p.is_active,
	}


def _event_payload(e: InventoryEvent, product_name: str | None = None) -> dict:
	return {
		"event_id": e.id,
		"product_id": e.product_id,
		"product_name": product_name,
		"event_type": e.event_type,
		"quantity_change": e.quantity_change,
		"new_stock_level": e.new_stock_level,
		"event_date": e.event_date.isoformat() if e.event_date else None,
		"notes": e.notes,
	}
