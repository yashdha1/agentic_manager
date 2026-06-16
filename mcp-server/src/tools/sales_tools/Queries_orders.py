from datetime import UTC

from core.db.pg_engine import get_async_session
from core.db.schemas import Order, OrderItem, OrderStatus, PaymentStatus
from core.logger import logger as log
from core.time_utils import now
from fastmcp import FastMCP
from sqlalchemy import and_, func, select

from .helpers import _as_float, _date_window, _normalize_enum

mcp = FastMCP("ecomm_mcp_sales_order_queries")


def _order_amounts_payload(order: Order) -> dict:
    tsubtotal = _as_float(order.subtotal)
    discount = _as_float(order.discount_amount)
    shipping = _as_float(order.shipping_amount)
    final_amount = tsubtotal - discount + shipping
    return {
        "order_id": order.id,
        "status": _normalize_enum(order.status),
        "payment_status": _normalize_enum(order.payment_status),
        "payment_method": order.payment_method,
        "device_type": order.device_type,
        "acquisition_channel": order.acquisition_channel,
        "shipping_country": order.shipping_country,
        "shipping_city": order.shipping_city,
        "subtotal": round(tsubtotal, 2),
        "discount_amount": round(discount, 2),
        "shipping_amount": round(shipping, 2),
        "final_amount": round(final_amount, 2),
        "ordered_at": order.ordered_at.isoformat() if order.ordered_at else None,
    }


@mcp.tool
async def sales_get_orders_by_channel(
    acquisition_channel: str,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 50,
) -> list[dict]:
    """
    Return orders for a given acquisition channel.

    Args:
            acquisition_channel: Exact channel name (case-insensitive).
            start_date: Optional start date in ISO format (YYYY-MM-DD).
            end_date: Optional end date in ISO format (YYYY-MM-DD).
            limit: Maximum number of rows.

    Returns:
            Order rows with revenue and item counts.
    """
    try:
        async with get_async_session() as session:
            stmt = (
                select(
                    Order.id,
                    Order.user_id,
                    Order.status,
                    Order.payment_status,
                    Order.ordered_at,
                    Order.acquisition_channel,
                    func.coalesce(func.sum(OrderItem.quantity), 0).label("units"),
                    func.coalesce(
                        func.sum(OrderItem.quantity * OrderItem.unit_price),
                        0,
                    ).label("revenue"),
                )
                .select_from(Order)
                .outerjoin(OrderItem, OrderItem.order_id == Order.id)
                .where(func.lower(Order.acquisition_channel) == acquisition_channel.lower())
                .group_by(
                    Order.id,
                    Order.user_id,
                    Order.status,
                    Order.payment_status,
                    Order.ordered_at,
                    Order.acquisition_channel,
                )
                .order_by(Order.ordered_at.desc())
                .limit(max(1, limit))
            )

            if start_date or end_date:
                if start_date and end_date:
                    start, end = _date_window(start_date, end_date)
                    start = start.replace(tzinfo=UTC)
                    end = end.replace(tzinfo=UTC)
                elif start_date:
                    start, _ = _date_window(start_date, start_date)
                    start = start.replace(tzinfo=UTC)
                    end = now()
                else:
                    start, end = _date_window("1970-01-01", end_date)
                    start = start.replace(tzinfo=UTC)
                    end = end.replace(tzinfo=UTC)

                stmt = stmt.where(and_(Order.ordered_at >= start, Order.ordered_at < end))

            rows = (await session.execute(stmt)).all()
            log.info(f"Retrieved {len(rows)} orders for channel='{acquisition_channel}'")
            return [
                {
                    "order_id": r.id,
                    "user_id": r.user_id,
                    "status": _normalize_enum(r.status),
                    "payment_status": _normalize_enum(r.payment_status),
                    "ordered_at": r.ordered_at.isoformat() if r.ordered_at else None,
                    "acquisition_channel": r.acquisition_channel,
                    "units": int(r.units or 0),
                    "revenue": round(_as_float(r.revenue), 2),
                }
                for r in rows
            ]
    except Exception as e:
        log.exception(f"Error in sales_get_orders_by_channel: {e}")
        return [{"error": str(e)}]


@mcp.tool
async def sales_get_orders_by_status(status: str, limit: int = 100) -> dict:
    """Filter orders by OrderStatus and return a small analysis summary."""
    try:
        parsed = OrderStatus(status.lower())
    except Exception:
        return {"error": "Invalid status", "allowed_status": [s.value for s in OrderStatus]}

    async with get_async_session() as session:
        stmt = (
            select(Order)
            .where(Order.status == parsed)
            .order_by(Order.ordered_at.desc())
            .limit(max(1, limit))
        )
        orders = (await session.execute(stmt)).scalars().all()

        rows = [_order_amounts_payload(o) for o in orders]
        total_final = round(sum(r["final_amount"] for r in rows), 2)
        log.info(f"Retrieved {len(rows)} orders by status={parsed.value}")
        return {
            "status": parsed.value,
            "count": len(rows),
            "total_final_amount": total_final,
            "orders": rows,
        }


@mcp.tool
async def sales_get_orders_by_device_type(device_type: str | None = None, limit: int = 100) -> dict:
    """Return orders split by device type and optional filtering by one device type."""
    async with get_async_session() as session:
        base_stmt = select(Order)
        if device_type:
            base_stmt = base_stmt.where(func.lower(Order.device_type) == device_type.lower())
        stmt = base_stmt.order_by(Order.ordered_at.desc()).limit(max(1, limit))
        orders = (await session.execute(stmt)).scalars().all()

        rows = [_order_amounts_payload(o) for o in orders]
        split: dict[str, int] = {}
        for r in rows:
            key = r["device_type"] or "unknown"
            split[key] = split.get(key, 0) + 1

        log.info(f"Retrieved {len(rows)} orders by device_type filter={device_type}")
        return {
            "device_type_filter": device_type,
            "count": len(rows),
            "device_split": split,
            "orders": rows,
        }


@mcp.tool
async def sales_get_orders_by_payment_status(payment_status: str, limit: int = 100) -> dict:
    """Filter orders by PaymentStatus enum."""
    try:
        parsed = PaymentStatus(payment_status.lower())
    except Exception:
        return {
            "error": "Invalid payment_status",
            "allowed_payment_status": [s.value for s in PaymentStatus],
        }

    async with get_async_session() as session:
        stmt = (
            select(Order)
            .where(Order.payment_status == parsed)
            .order_by(Order.ordered_at.desc())
            .limit(max(1, limit))
        )
        orders = (await session.execute(stmt)).scalars().all()

        rows = [_order_amounts_payload(o) for o in orders]
        total_final = round(sum(r["final_amount"] for r in rows), 2)
        log.info(f"Retrieved {len(rows)} orders by payment_status={parsed.value}")
        return {
            "payment_status": parsed.value,
            "count": len(rows),
            "total_final_amount": total_final,
            "orders": rows,
        }


@mcp.tool
async def sales_get_orders_by_amount(
    min_subtotal: float | None = None,
    max_subtotal: float | None = None,
    min_discount_amount: float | None = None,
    max_discount_amount: float | None = None,
    min_shipping_amount: float | None = None,
    max_shipping_amount: float | None = None,
    limit: int = 100,
) -> dict:
    """Filter orders by amount fields (subtotal, discount, shipping) and return amount analysis."""
    filters = []
    if min_subtotal is not None:
        filters.append(Order.subtotal >= min_subtotal)
    if max_subtotal is not None:
        filters.append(Order.subtotal <= max_subtotal)
    if min_discount_amount is not None:
        filters.append(Order.discount_amount >= min_discount_amount)
    if max_discount_amount is not None:
        filters.append(Order.discount_amount <= max_discount_amount)
    if min_shipping_amount is not None:
        filters.append(Order.shipping_amount >= min_shipping_amount)
    if max_shipping_amount is not None:
        filters.append(Order.shipping_amount <= max_shipping_amount)

    async with get_async_session() as session:
        stmt = select(Order)
        if filters:
            stmt = stmt.where(and_(*filters))
        stmt = stmt.order_by(Order.ordered_at.desc()).limit(max(1, limit))
        orders = (await session.execute(stmt)).scalars().all()

        rows = [_order_amounts_payload(o) for o in orders]
        summary = {
            "subtotal_sum": round(sum(r["subtotal"] for r in rows), 2),
            "discount_sum": round(sum(r["discount_amount"] for r in rows), 2),
            "shipping_sum": round(sum(r["shipping_amount"] for r in rows), 2),
            "final_amount_sum": round(sum(r["final_amount"] for r in rows), 2),
        }

        log.info(f"Retrieved {len(rows)} orders by amount filters")
        return {
            "count": len(rows),
            "filters_applied": {
                "min_subtotal": min_subtotal,
                "max_subtotal": max_subtotal,
                "min_discount_amount": min_discount_amount,
                "max_discount_amount": max_discount_amount,
                "min_shipping_amount": min_shipping_amount,
                "max_shipping_amount": max_shipping_amount,
            },
            "summary": summary,
            "orders": rows,
        }


@mcp.tool
async def sales_get_orders_by_place(
    acquisition_channel: str | None = None, limit: int = 100
) -> dict:
    """Return channel-based order divisions with optional acquisition_channel filter."""
    async with get_async_session() as session:
        stmt = select(Order)
        if acquisition_channel:
            stmt = stmt.where(func.lower(Order.acquisition_channel) == acquisition_channel.lower())
        stmt = stmt.order_by(Order.ordered_at.desc()).limit(max(1, limit))
        orders = (await session.execute(stmt)).scalars().all()

        rows = [_order_amounts_payload(o) for o in orders]
        channel_split: dict[str, int] = {}
        for r in rows:
            key = r["acquisition_channel"] or "unknown"
            channel_split[key] = channel_split.get(key, 0) + 1

        log.info(
            f"Retrieved {len(rows)} orders by acquisition_channel filter={acquisition_channel}"
        )
        return {
            "acquisition_channel_filter": acquisition_channel,
            "count": len(rows),
            "channel_split": channel_split,
            "orders": rows,
        }


@mcp.tool
async def sales_get_orders_by_payment_method(payment_method: str, limit: int = 100) -> dict:
    """Filter orders by payment_method (case-insensitive exact match)."""
    async with get_async_session() as session:
        stmt = (
            select(Order)
            .where(func.lower(Order.payment_method) == payment_method.lower())
            .order_by(Order.ordered_at.desc())
            .limit(max(1, limit))
        )
        orders = (await session.execute(stmt)).scalars().all()

        rows = [_order_amounts_payload(o) for o in orders]
        total_final = round(sum(r["final_amount"] for r in rows), 2)
        log.info(f"Retrieved {len(rows)} orders by payment_method={payment_method}")
        return {
            "payment_method": payment_method,
            "count": len(rows),
            "total_final_amount": total_final,
            "orders": rows,
        }
