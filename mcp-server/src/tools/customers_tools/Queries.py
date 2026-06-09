import uuid

from core.db.pg_engine import get_async_session
from core.db.schemas import Email, User
from core.time_utils import now
from fastmcp import FastMCP
from sqlalchemy import select

mcp = FastMCP("ecomm_mcp_customer_commands")


@mcp.tool
async def customers_send_subscribed_users_newsletter_hitl(
    subject: str,
    body: str,
    html_body: str | None = None,
) -> dict:
    """
    Send a newsletter email to all users with newsletter subscription enabled.

    Requires human approval before executing — the HITL middleware intercepts
    this call and raises a LangGraph interrupt. The email record is only inserted
    after the operator approves.

    Args:
        subject:   Email subject line.
        body:      Plain-text email body. 
    """
    async with get_async_session() as session:
        stmt = select(User.email).where(User.has_newsletter.is_(True))
        result = await session.execute(stmt)
        subscriber_emails = [row[0] for row in result.all()]

        if not subscriber_emails:
            return {"status": "no_subscribers", "message": "No subscribed users found."}

        ts = now()
        record = Email(
            message_id=str(uuid.uuid4()),
            recipients=subscriber_emails,
            subject=subject,
            body=body, 
            status="sent",
            is_read=False,
            received_at=ts,
            sent_at=ts,
            created_at=ts,
        )
        session.add(record)
        await session.commit()

        return {
            "status": "sent",
            "message_id": record.message_id,
            "recipient_count": len(subscriber_emails),
        }
