from core.db.pg_engine import get_async_session
from core.db.schemas import InventoryEvent, Order, OrderStatus, Product
from core.logger import logger as log
from core.time_utils import now
from fastmcp import FastMCP

mcp = FastMCP("ecomm_mcp_sales_commands")
HITL_CONFIRM_INSTRUCTION = "Review and call again with confirmed=True to apply."


def _parse_order_status(status: str) -> OrderStatus:
	return OrderStatus(status.lower())


@mcp.tool
async def update_product_status(product_id: int, is_active: bool, confirmed: bool = False) -> dict:
	"""
	HITL tool to update a product active status.

	Step 1: call with confirmed=False to preview.
	Step 2: call with confirmed=True to apply update.
	"""
	async with get_async_session() as session:
		product = await session.get(Product, product_id)
		if not product:
			return {"error": f"Product {product_id} not found"}

		if not confirmed:
			return {
				"preview": True,
				"product_id": product.id,
				"current_is_active": product.is_active,
				"new_is_active": is_active,
				"instructions": HITL_CONFIRM_INSTRUCTION,
			}

		product.is_active = is_active
		product.updated_at = now()

		log.info(f"Updated product {product_id} status is_active={is_active}")
		return {
			"status": "updated",
			"product_id": product.id,
			"is_active": product.is_active,
		}

@mcp.tool
async def update_product_details(
	product_id: int,
	name: str | None = None,
	description: str | None = None,
	category: str | None = None,
	sub_category: str | None = None,
	brand: str | None = None,
	price: float | None = None,
	cost_price: float | None = None,
	confirmed: bool = False,
) -> dict:
	"""
	HITL tool to update product details.

	Step 1: call with confirmed=False to preview.
	Step 2: call with confirmed=True to apply update.
	"""
	updates = {
		"name": name,
		"description": description,
		"category": category,
		"sub_category": sub_category,
		"brand": brand,
		"price": price,
		"cost_price": cost_price,
	}
	updates = {k: v for k, v in updates.items() if v is not None}

	if not updates:
		return {"error": "No fields provided to update"}

	async with get_async_session() as session:
		product = await session.get(Product, product_id)
		if not product:
			return {"error": f"Product {product_id} not found"}

		if not confirmed:
			return {
				"preview": True,
				"product_id": product.id,
				"current": {
					"name": product.name,
					"description": product.description,
					"category": product.category,
					"sub_category": product.sub_category,
					"brand": product.brand,
					"price": float(product.price) if product.price is not None else None,
			"cost_price": float(product.cost_price) if product.cost_price is not None else None,
				},
				"updates": updates,
				"instructions": HITL_CONFIRM_INSTRUCTION,
			}

		for field, value in updates.items():
			setattr(product, field, value)
		product.updated_at = now()

		log.info(f"Updated product {product_id} details fields={list(updates.keys())}")
		return {
			"status": "updated",
			"product_id": product.id,
			"updated_fields": sorted(updates.keys()),
		}

@mcp.tool
async def update_order_status(order_id: int, status: str, confirmed: bool = False) -> dict:
	"""
	HITL tool to update order status.

	Step 1: call with confirmed=False to preview.
	Step 2: call with confirmed=True to apply update.
	"""
	try:
		new_status = _parse_order_status(status)
	except Exception:
		return {
			"error": "Invalid status",
			"allowed_status": [s.value for s in OrderStatus],
		}

	async with get_async_session() as session:
		order = await session.get(Order, order_id)
		if not order:
			return {"error": f"Order {order_id} not found"}

		current_status = order.status.value if hasattr(order.status, "value") else str(order.status)

		if not confirmed:
			return {
				"preview": True,
				"order_id": order.id,
				"current_status": current_status,
				"new_status": new_status.value,
				"instructions": HITL_CONFIRM_INSTRUCTION,
			}

		order.status = new_status

		log.info(f"Updated order {order_id} status to {new_status.value}")
		return {
			"status": "updated",
			"order_id": order.id,
			"order_status": new_status.value,
		}

@mcp.tool
async def update_product_stock(
	product_id: int, 
	restock_quantity: int, 
	confirmed: bool = False) -> dict:
	"""
	HITL tool for product restock.

	Step 1: call with confirmed=False to preview.
	Step 2: call with confirmed=True to apply stock increase and log inventory event.
	"""
	if restock_quantity <= 0:
		return {"error": "restock_quantity must be greater than 0"}

	async with get_async_session() as session:
		product = await session.get(Product, product_id)
		if not product:
			return {"error": f"Product {product_id} not found"}

		old_stock = int(product.stock_quantity or 0)
		new_stock = old_stock + restock_quantity

		if not confirmed:
			return {
				"preview": True,
				"product_id": product.id,
				"current_stock": old_stock,
				"restock_quantity": restock_quantity,
				"new_stock": new_stock,
				"instructions": HITL_CONFIRM_INSTRUCTION,
			}

		product.stock_quantity = new_stock
		product.updated_at = now()
		event = InventoryEvent(
			product_id=product.id,
			event_type="restock",
			quantity_change=restock_quantity,
			new_stock_level=new_stock,
			event_date=now(),
			notes="HITL restock update_product_stock",
		)
		session.add(event)

		log.info(f"Restocked product {product_id} by {restock_quantity} to {new_stock}")
		return {
			"status": "updated",
			"product_id": product.id,
			"old_stock": old_stock,
			"restock_quantity": restock_quantity,
			"new_stock": new_stock,
			"inventory_event_type": "restock",
		}
