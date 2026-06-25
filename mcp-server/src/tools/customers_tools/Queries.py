import uuid

from core.db.pg_engine import get_async_session
from core.db.schemas import Email, User
from core.logger import logger as log
from core.time_utils import now
from fastmcp import FastMCP
from sqlalchemy import select

mcp = FastMCP("ecomm_mcp_customer_commands")


@mcp.tool
async def customers_send_subscribed_users_newsletter_hitl(
    subject: str,
    body: str
) -> dict:
    """
    Send a newsletter to every user who has opted in to the newsletter.

    Call this tool with ONLY the subject and body — it looks up all
    subscribed users internally. Do NOT ask for or collect subscriber
    emails before calling this tool.

    Note: a human-approval step is automatically triggered before
    dispatch; you do not need to handle that — just call the tool.

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
        log.info(f"Sent newsletter to {len(subscriber_emails)} subscribers with subject: '{subject}'")

        return {
            "status": "sent",
            "message_id": record.message_id,
            "recipient_count": len(subscriber_emails),
        }
