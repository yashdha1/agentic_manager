from datetime import UTC

from core.db.pg_engine import get_async_session
from core.db.schemas import Order, OrderItem, Refund, RefundStatus
from core.logger import logger as log
from fastmcp import FastMCP
from sqlalchemy import and_, func, select

from tools.inventory_tools.helpers import _refund_payload
from tools.sales_tools.helpers import _as_float, _date_window

mcp = FastMCP("ecomm_mcp_inventory_refund_queries")


@mcp.tool
async def inventory_get_refund_rate_trend(
	start_date: str,
	end_date: str,
	granularity: str = "month",
) -> list[dict]:
	"""
	Return refund count and total refund amount grouped by time period.

	Useful for identifying trends in refund volume over a date range.
	``granularity`` controls the bucket size.

	Args:
		start_date: Window start in ISO format (``YYYY-MM-DD``), inclusive.
		end_date: Window end in ISO format (``YYYY-MM-DD``), inclusive.
		granularity: Time bucket — ``day``, ``week``, or ``month``. Defaults to ``month``.

	Returns:
		List of period dicts with ``period``, ``refund_count``, and ``total_refund_amount``,
		ordered chronologically.
	"""
	_VALID = {"day", "week", "month"}
	if granularity not in _VALID:
		return [{"error": f"granularity must be one of {sorted(_VALID)}"}]

	try:
		start, end = _date_window(start_date, end_date)
		start = start.replace(tzinfo=UTC)
		end = end.replace(tzinfo=UTC)

		async with get_async_session() as session:
			period_expr = func.date_trunc(granularity, Refund.processed_at)
			stmt = (
				select(
					period_expr.label("period"),
					func.count(Refund.id).label("refund_count"),
					func.coalesce(func.sum(Refund.refund_amount), 0).label("total_refund_amount"),
				)
				.where(
					and_(
						Refund.processed_at >= start,
						Refund.processed_at < end,
					)
				)
				.group_by(period_expr)
				.order_by(period_expr)
			)
			rows = (await session.execute(stmt)).all()
			log.info(f"inventory_get_refund_rate_trend: {len(rows)} periods for {granularity}")
			return [
				{
					"period": r.period.isoformat() if r.period else None,
					"refund_count": int(r.refund_count),
					"total_refund_amount": round(_as_float(r.total_refund_amount), 2),
				}
				for r in rows
			]
	except Exception as e:
		log.exception(f"Error in inventory_get_refund_rate_trend: {e}")
		return [{"error": str(e)}]


@mcp.tool
async def inventory_get_refund_by_status(
	status: str,
	limit: int = 100,
) -> dict:
	"""
	Return all refund records matching a given status with a summary.

	Args:
		status: One of ``pending``, ``approved``, ``rejected``, or ``processed``
			(case-insensitive).
		limit: Maximum number of rows to return. Defaults to 100.

	Returns:
		Dict with ``status``, ``count``, ``total_refund_amount``, and ``refunds`` list.
		Returns ``{"error": ..., "allowed_status": [...]}`` for invalid status values.
	"""
	try:
		parsed = RefundStatus(status.lower())
	except ValueError:
		return {"error": "Invalid status", "allowed_status": [s.value for s in RefundStatus]}

	try:
		async with get_async_session() as session:
			stmt = (
				select(Refund, Order.user_id)
				.join(Order, Order.id == Refund.order_id)
				.where(Refund.status == parsed)
				.order_by(Refund.processed_at.desc().nullslast())
				.limit(max(1, limit))
			)
			rows = (await session.execute(stmt)).all()
			refunds = [_refund_payload(r, uid) for r, uid in rows]
			total = round(sum(r["refund_amount"] for r in refunds), 2)
			log.info(f"inventory_get_refund_by_status: status={parsed.value} -> "
			f"{len(refunds)} rows")
			return {
				"status": parsed.value,
				"count": len(refunds),
				"total_refund_amount": total,
				"refunds": refunds,
			}
	except Exception as e:
		log.exception(f"Error in inventory_get_refund_by_status: {e}")
		return {"error": str(e)}


@mcp.tool
async def inventory_get_refund_history_user(
	user_id: int,
	status: str | None = None,
	limit: int = 50,
) -> dict:
	"""
	Return the complete refund history for a specific user.

	Args:
		user_id: The user whose refunds to retrieve.
		status: Optional filter on refund status
			(``pending`` | ``approved`` | ``rejected`` | ``processed``).
		limit: Maximum number of rows to return. Defaults to 50.

	Returns:
		Dict with ``user_id``, ``count``, ``total_refund_amount``, and ``refunds`` list.
	"""
	try:
		async with get_async_session() as session:
			stmt = (
				select(Refund)
				.join(Order, Order.id == Refund.order_id)
				.where(Order.user_id == user_id)
				.order_by(Refund.processed_at.desc().nullslast())
			)

			if status is not None:
				try:
					stmt = stmt.where(Refund.status == RefundStatus(status.lower()))
				except ValueError:
					return {
						"error": "Invalid status", 
						"allowed_status": [s.value for s in RefundStatus]
					}

			stmt = stmt.limit(max(1, limit))
			refunds_db = (await session.execute(stmt)).scalars().all()
			refunds = [_refund_payload(r, user_id) for r in refunds_db]
			total = round(sum(r["refund_amount"] for r in refunds), 2)
			log.info(f"inventory_get_refund_history_user: user_id={user_id} -> {len(refunds)} rows")
			return {
				"user_id": user_id,
				"count": len(refunds),
				"total_refund_amount": total,
				"refunds": refunds,
			}
	except Exception as e:
		log.exception(f"Error in inventory_get_refund_history_user: {e}")
		return {"error": str(e)}


@mcp.tool
async def inventory_get_refund_history_product(
	product_id: int,
	status: str | None = None,
	limit: int = 50,
) -> dict:
	"""
	Return all refunds linked to orders that contain a specific product.

	Joins ``refunds → orders → order_items`` to find refunds tied to the product.

	Args:
		product_id: The product whose refund history to retrieve.
		status: Optional filter on refund status
			(``pending`` | ``approved`` | ``rejected`` | ``processed``).
		limit: Maximum number of rows to return. Defaults to 50.

	Returns:
		Dict with ``product_id``, ``count``, ``total_refund_amount``, and ``refunds`` list.
	"""
	try:
		async with get_async_session() as session:
			stmt = (
				select(Refund, Order.user_id)
				.join(Order, Order.id == Refund.order_id)
				.join(OrderItem, OrderItem.order_id == Order.id)
				.where(OrderItem.product_id == product_id)
				.order_by(Refund.processed_at.desc().nullslast())
				.distinct(Refund.id)
			)

			if status is not None:
				try:
					stmt = stmt.where(Refund.status == RefundStatus(status.lower()))
				except ValueError:
					return {
						"error": "Invalid status", 
						"allowed_status": [s.value for s in RefundStatus]
					}

			stmt = stmt.limit(max(1, limit))
			rows = (await session.execute(stmt)).all()
			refunds = [_refund_payload(r, uid) for r, uid in rows]
			total = round(sum(r["refund_amount"] for r in refunds), 2)
			log.info(f"inventory_get_refund_history_product: product_id={product_id} ->"
			f"{len(refunds)} rows")
			
			return {
				"product_id": product_id,
				"count": len(refunds),
				"total_refund_amount": total,
				"refunds": refunds,
			}
	except Exception as e:
		log.exception(f"Error in inventory_get_refund_history_product: {e}")
		return {"error": str(e)}