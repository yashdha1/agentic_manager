from datetime import UTC

from core.db.pg_engine import get_async_session
from core.db.schemas import InventoryEvent, Product
from core.logger import logger as log
from fastmcp import FastMCP
from sqlalchemy import and_, select

from tools.inventory_tools.helpers import _event_payload, _product_payload
from tools.sales_tools.helpers import _date_window

mcp = FastMCP("ecomm_mcp_inventory_queries")


@mcp.tool
async def inventory_get_status(
    category: str | None = None,
    brand: str | None = None,
    sku: str | None = None,
    is_active: bool | None = None,
    low_stock_threshold: int | None = None,
    limit: int = 100,
) -> list[dict]:
    """
    Return current stock levels for products with optional filters.

    Reads the ``products`` table which holds the live ``stock_quantity`` column.
    All string filters are case-insensitive.

    Args:
            category: Filter by product category (exact match, case-insensitive).
            brand: Filter by brand name (exact match, case-insensitive).
            sku: Filter by SKU (exact match, case-insensitive).
            is_active: When provided, restricts to active (True) or inactive (False) products.
            low_stock_threshold: When provided, returns only products whose
                    ``stock_quantity`` is strictly below this value.
            limit: Maximum number of rows to return. Defaults to 100.

    Returns:
            List of product dicts with ``product_id``, ``sku``, ``name``,
            ``category``, ``sub_category``, ``brand``, ``stock_quantity``,
            ``price``, and ``is_active``.
    """
    try:
        async with get_async_session() as session:
            stmt = select(Product).order_by(Product.stock_quantity.asc())

            filters = []
            if category is not None:
                filters.append(Product.category.ilike(category))
            if brand is not None:
                filters.append(Product.brand.ilike(brand))
            if sku is not None:
                filters.append(Product.sku.ilike(sku))
            if is_active is not None:
                filters.append(Product.is_active.is_(is_active))
            if low_stock_threshold is not None:
                filters.append(Product.stock_quantity < low_stock_threshold)
            if filters:
                stmt = stmt.where(and_(*filters))

            stmt = stmt.limit(max(1, limit))
            products = (await session.execute(stmt)).scalars().all()
            log.info(f"inventory_get_status returned {len(products)} products")
            return [_product_payload(p) for p in products]
    except Exception as e:
        log.exception(f"Error in inventory_get_status: {e}")
        return [{"error": str(e)}]


@mcp.tool
async def inventory_get_details_by_event(
    event_type: str,
    product_id: int | None = None,
    sku: str | None = None,
    limit: int = 100,
) -> list[dict]:
    """
    Return inventory event records filtered by event type.

    Allowed ``event_type`` values: ``sale_deduction``, ``restock``, ``adjustment``.
    Optionally narrows results to a single product via ``product_id`` or ``sku``.

    Args:
            event_type: The inventory event type to filter on
                    (``sale_deduction`` | ``restock`` | ``adjustment``).
            product_id: Optional product ID to scope the query.
            sku: Optional product SKU to scope the query (case-insensitive).
                    Ignored when ``product_id`` is provided.
            limit: Maximum number of rows to return. Defaults to 100.

    Returns:
            List of event dicts with ``event_id``, ``product_id``, ``product_name``,
            ``event_type``, ``quantity_change``, ``new_stock_level``, ``event_date``,
            and ``notes``.
    """
    try:
        async with get_async_session() as session:
            stmt = (
                select(InventoryEvent, Product.name)
                .join(Product, Product.id == InventoryEvent.product_id)
                .where(InventoryEvent.event_type == event_type.lower())
                .order_by(InventoryEvent.event_date.desc())
            )

            if product_id is not None:
                stmt = stmt.where(InventoryEvent.product_id == product_id)
            elif sku is not None:
                stmt = stmt.where(Product.sku.ilike(sku))

            stmt = stmt.limit(max(1, limit))
            rows = (await session.execute(stmt)).all()
            log.info(
                f"inventory_get_details_by_event: event_type='{event_type}' -> {len(rows)} rows"
            )
            return [_event_payload(event, name) for event, name in rows]
    except Exception as e:
        log.exception(f"Error in inventory_get_details_by_event: {e}")
        return [{"error": str(e)}]


@mcp.tool
async def inventory_get_details_by_time(
    start_date: str,
    end_date: str,
    event_type: str | None = None,
    product_id: int | None = None,
    limit: int = 100,
) -> list[dict]:
    """
    Return inventory events that occurred within a date window.

    Args:
            start_date: Window start in ISO format (``YYYY-MM-DD``), inclusive.
            end_date: Window end in ISO format (``YYYY-MM-DD``), inclusive.
            event_type: Optional filter on event type
                    (``sale_deduction`` | ``restock`` | ``adjustment``).
            product_id: Optional product ID to narrow results to a single product.
            limit: Maximum number of rows to return. Defaults to 100.

    Returns:
            List of event dicts with ``event_id``, ``product_id``, ``product_name``,
            ``event_type``, ``quantity_change``, ``new_stock_level``, ``event_date``,
            and ``notes``.
    """
    try:
        start, end = _date_window(start_date, end_date)
        start = start.replace(tzinfo=UTC)
        end = end.replace(tzinfo=UTC)

        async with get_async_session() as session:
            stmt = (
                select(InventoryEvent, Product.name)
                .join(Product, Product.id == InventoryEvent.product_id)
                .where(
                    and_(
                        InventoryEvent.event_date >= start,
                        InventoryEvent.event_date < end,
                    )
                )
                .order_by(InventoryEvent.event_date.desc())
            )

            if event_type is not None:
                stmt = stmt.where(InventoryEvent.event_type == event_type.lower())
            if product_id is not None:
                stmt = stmt.where(InventoryEvent.product_id == product_id)

            stmt = stmt.limit(max(1, limit))
            rows = (await session.execute(stmt)).all()
            log.info(f"inventory_get_details_by_time: {start_date}→{end_date} -> {len(rows)} rows")
            return [_event_payload(event, name) for event, name in rows]
    except Exception as e:
        log.exception(f"Error in inventory_get_details_by_time: {e}")
        return [{"error": str(e)}]