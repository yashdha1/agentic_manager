import uuid

from core.db.pg_engine import get_async_session
from core.db.schemas import Email, User
from core.time_utils import now
from fastmcp import FastMCP
from sqlalchemy import select

mcp = FastMCP("ecomm_mcp_customer_commands")


@mcp.tool
async def customers_send_subscribed_users_newsletter(
    subject: str,
    body: str,
    html_body: str | None = None,
    confirmed: bool = False,
) -> dict:
    """
    Send a newsletter email to all users with newsletter subscription enabled.

    This is a two-step HITL (Human-in-the-Loop) tool:
    - Step 1 — confirmed=False (default): queries subscribed users and returns a preview
      showing recipient count, addresses, subject, and body. No database write occurs.
    - Step 2 — confirmed=True: inserts a single Email record into the emails table with
      all subscriber addresses in the recipients array and status='sent'.

    Always call with confirmed=False first,
    (Human-in-the-Loop) (HITL) review the preview, then call again
    with confirmed=True to complete the send.

    Source (read):  users table  — filters on has_newsletter = True.
    Source (write): emails table — one record inserted on confirmation.
    """
    async with get_async_session() as session:
        stmt = select(User.email).where(User.has_newsletter.is_(True))
        result = await session.execute(stmt)
        subscriber_emails = [row[0] for row in result.all()]

        if not subscriber_emails:
            return {"status": "no_subscribers", "message": "No subscribed users found."}

        if not confirmed:
            return {
                "preview": True,
                "recipient_count": len(subscriber_emails),
                "recipients": subscriber_emails,
                "subject": subject,
                "body": body,
                "html_body": html_body,
                "instructions": "Review the above, then call again with confirmed=True to send.",
            }

        ts = now()
        record = Email(
            message_id=str(uuid.uuid4()),
            recipients=subscriber_emails,
            subject=subject,
            body=body,
            html_body=html_body,
            status="sent",
            is_read=False,
            received_at=ts,
            sent_at=ts,
            created_at=ts,
        )
        session.add(record)

        return {
            "status": "sent",
            "message_id": record.message_id,
            "recipient_count": len(subscriber_emails),
        }
