from core.db.pg_engine import get_async_session
from core.db.schemas import Order, Refund, RefundStatus
from core.logger import logger as log
from core.time_utils import now
from fastmcp import FastMCP
from sqlalchemy import select, func

mcp = FastMCP("ecomm_mcp_inventory_commands")
HITL_CONFIRM_INSTRUCTION = "Review and call again with confirmed=True to apply."


@mcp.tool
async def inventory_create_refund(
	order_id: int,
	refund_amount: float,
	reason: str,
	confirmed: bool = False,
) -> dict:
	"""
	HITL tool to create a refund record for an order.

	Validates that the order exists and that ``refund_amount`` does not exceed
	the order subtotal before committing. The total of existing refunds for the
	order is also checked so cumulative refunds cannot exceed the subtotal.

	Step 1 — ``confirmed=False`` (default): validates inputs and returns a preview
		showing order details, existing refund total, and proposed refund. No write occurs.
	Step 2 — ``confirmed=True``: inserts the ``Refund`` row with
		``status=pending`` and ``processed_at`` set to the current UTC time.

	Args:
		order_id: ID of the order to refund.
		refund_amount: Positive amount to refund (must not exceed the refundable balance).
		reason: Human-readable reason for the refund.
		confirmed: Set to ``True`` to commit after reviewing the preview.

	Returns:
		Preview dict on Step 1, or created refund details on Step 2.
		Returns ``{"error": ...}`` on validation failure.
	"""
	if refund_amount <= 0:
		return {"error": "refund_amount must be greater than 0"}

	async with get_async_session() as session:
		order = await session.get(Order, order_id)
		if not order:
			return {"error": f"Order {order_id} not found"}

		subtotal = float(order.subtotal or 0)

		# Sum of refunds already issued for this order
		existing_total_result = await session.execute(
			select(func.coalesce(func.sum(Refund.refund_amount), 0)).where(
				Refund.order_id == order_id
			)
		)
		existing_total = float(existing_total_result.scalar())
		refundable_balance = round(subtotal - existing_total, 2)

		if refund_amount > refundable_balance:
			return {
				"error": "refund_amount exceeds refundable balance",
				"subtotal": subtotal,
				"already_refunded": round(existing_total, 2),
				"refundable_balance": refundable_balance,
			}

		if not confirmed:
			return {
				"preview": True,
				"order_id": order_id,
				"user_id": order.user_id,
				"order_status": order.status.value if hasattr(order.status, "value") else str(order.status),
				"subtotal": subtotal,
				"already_refunded": round(existing_total, 2),
				"refundable_balance": refundable_balance,
				"proposed_refund_amount": refund_amount,
				"reason": reason,
				"instructions": HITL_CONFIRM_INSTRUCTION,
			}

		refund = Refund(
			order_id=order_id,
			refund_amount=refund_amount,
			reason=reason,
			status=RefundStatus.PENDING,
			processed_at=now(),
		)
		session.add(refund)
		await session.flush()

		log.info(f"Created refund for order {order_id}: amount={refund_amount}")
		return {
			"status": "created",
			"refund_id": refund.id,
			"order_id": order_id,
			"user_id": order.user_id,
			"refund_amount": refund_amount,
			"reason": reason,
			"refund_status": RefundStatus.PENDING.value,
		}
