from core.db.pg_engine import get_async_session
from core.db.schemas import InventoryEvent, Order, OrderStatus, Product
from core.logger import logger as log
from core.time_utils import now
from fastmcp import FastMCP

mcp = FastMCP("ecomm_mcp_sales_commands")


def _parse_order_status(status: str) -> OrderStatus:
    return OrderStatus(status.lower())


@mcp.tool
async def sales_update_product_status_hitl(product_id: int, is_active: bool) -> dict:
    """
    Update a product's active/inactive status.

    Requires human approval before executing — the HITL middleware intercepts
    this call and raises a LangGraph interrupt. The update is only applied after
    the operator approves.

    Args:
        product_id: ID of the product to update.
        is_active:  New active status.
    """
    async with get_async_session() as session:
        product = await session.get(Product, product_id)
        if not product:
            return {"error": f"Product {product_id} not found"}

        product.is_active = is_active
        product.updated_at = now()

        log.info(f"Updated product {product_id} status is_active={is_active}")
        return {
            "status": "updated",
            "product_id": product.id,
            "is_active": product.is_active,
        }


@mcp.tool
async def sales_update_product_details_hitl(
    product_id: int,
    name: str | None = None,
    description: str | None = None,
    category: str | None = None,
    sub_category: str | None = None,
    brand: str | None = None,
    price: float | None = None,
    cost_price: float | None = None,
) -> dict:
    """
    Update product details (name, description, category, brand, price, etc.).

    Requires human approval before executing — the HITL middleware intercepts
    this call and raises a LangGraph interrupt. Only supplied (non-None) fields
    are updated.

    Args:
        product_id:   ID of the product to update.
        name:         New product name, or None to leave unchanged.
        description:  New description, or None to leave unchanged.
        category:     New category, or None to leave unchanged.
        sub_category: New sub-category, or None to leave unchanged.
        brand:        New brand, or None to leave unchanged.
        price:        New price, or None to leave unchanged.
        cost_price:   New cost price, or None to leave unchanged.
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
async def sales_update_order_status_hitl(order_id: int, status: str) -> dict:
    """
    Update an order's status.

    Requires human approval before executing — the HITL middleware intercepts
    this call and raises a LangGraph interrupt. The status change is only applied
    after the operator approves.

    Args:
        order_id: ID of the order to update.
        status:   New order status (e.g. 'shipped', 'cancelled', 'delivered').
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

        order.status = new_status

        log.info(f"Updated order {order_id} status to {new_status.value}")
        return {
            "status": "updated",
            "order_id": order.id,
            "order_status": new_status.value,
        }


@mcp.tool
async def sales_update_product_stock_hitl(product_id: int, restock_quantity: int) -> dict:
    """
    Restock a product by adding to its current stock quantity.

    Requires human approval before executing — the HITL middleware intercepts
    this call and raises a LangGraph interrupt. The stock increase and inventory
    event are only committed after the operator approves.

    Args:
        product_id:        ID of the product to restock.
        restock_quantity:  Quantity to add (must be > 0).
    """
    if restock_quantity <= 0:
        return {"error": "restock_quantity must be greater than 0"}

    async with get_async_session() as session:
        product = await session.get(Product, product_id)
        if not product:
            return {"error": f"Product {product_id} not found"}

        old_stock = int(product.stock_quantity or 0)
        new_stock = old_stock + restock_quantity

        product.stock_quantity = new_stock
        product.updated_at = now()
        event = InventoryEvent(
            product_id=product.id,
            event_type="restock",
            quantity_change=restock_quantity,
            new_stock_level=new_stock,
            event_date=now(),
            notes="HITL restock sales_update_product_stock_hitl",
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