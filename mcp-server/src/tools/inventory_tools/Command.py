from core.db.pg_engine import get_async_session
from core.db.schemas import Order, Refund, RefundStatus
from core.logger import logger as log
from core.time_utils import now
from fastmcp import FastMCP
from sqlalchemy import func, select

mcp = FastMCP("ecomm_mcp_inventory_commands")


@mcp.tool
async def inventory_create_refund_hitl(
    order_id: int,
    reason: str,
) -> dict:
    """
    Create a full refund for an order.

    Requires human approval before executing — the HITL middleware intercepts
    this call and raises a LangGraph interrupt showing the proposed action.
    The refund is only committed after the operator approves.

    Refunds the full remaining refundable balance (order subtotal minus any
    previously issued refunds).

    Args:
        order_id: ID of the order to refund.
        reason:   Human-readable reason for the refund.

    Returns:
        Created refund details on success.
        ``{"error": ...}`` if the order is not found or has no refundable balance.
    """
    async with get_async_session() as session:
        order = await session.get(Order, order_id)
        if not order:
            return {"error": f"Order {order_id} not found"}

        subtotal = float(order.subtotal or 0)

        existing_total_result = await session.execute(
            select(func.coalesce(func.sum(Refund.refund_amount), 0)).where(
                Refund.order_id == order_id
            )
        )
        existing_total = float(existing_total_result.scalar())
        refundable_balance = round(subtotal - existing_total, 2)

        if refundable_balance <= 0:
            return {
                "error": "No refundable balance remaining for this order",
                "subtotal": subtotal,
                "already_refunded": round(existing_total, 2),
            }

        refund = Refund(
            order_id=order_id,
            refund_amount=refundable_balance,
            reason=reason,
            status=RefundStatus.PENDING,
            processed_at=now(),
        )
        session.add(refund)
        await session.commit()

        log.info(f"Created full refund for order {order_id}: amount={refundable_balance}")
        return {
            "status": "created",
            "refund_id": refund.id,
            "order_id": order_id,
            "user_id": order.user_id,
            "refund_amount": refundable_balance,
            "reason": reason,
            "refund_status": RefundStatus.PENDING.value,
        }
