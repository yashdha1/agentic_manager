from core.db.pg_engine import get_async_session
from core.db.schemas import Order, Review, User
from core.logger import logger as log
from fastmcp import FastMCP
from sqlalchemy import func, select

mcp = FastMCP("ecomm_mcp_customer_queries")


@mcp.tool
async def customers_get_user_by_id(user_id: int) -> dict:
    """
    Retrieve full details for a customer by their user ID.

    Use this tool when you need all profile information for a specific
    customer, including contact details, location, tier, and account status.

    Args:
        user_id: Unique user identifier.

    Returns:
        All user profile fields, or an error if the user cannot be found.
    """
    async with get_async_session() as session:
        row = await session.get(User, user_id)
        if not row:
            return {"error": f"User {user_id} not found"}
        log.info(f"Retrieved user {user_id}: {row.first_name} {row.last_name}, email: {row.email}")
        return {
            "id": row.id,
            "first_name": row.first_name,
            "last_name": row.last_name,
            "email": row.email,
            "phone": row.phone,
            "country": row.country,
            "city": row.city,
            "postcode": row.postcode,
            "is_active": row.is_active,
            "customer_tier": row.customer_tier,
            "has_newsletter": row.has_newsletter,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }


@mcp.tool
async def customers_get_user_by_name(name: str, surname: str) -> dict:
    """
    Find a customer by their first and last name.

    Use this tool when you have a customer's name and need to look up
    their profile.

    Args:
        name: Customer's first name (case-insensitive).
        surname: Customer's last name (case-insensitive).

    Returns:
        The matching user's profile, or an error if no user is found.
    """
    async with get_async_session() as session:
        stmt = select(User).where(
            func.lower(User.first_name) == name.lower(),
            func.lower(User.last_name) == surname.lower(),
        )
        result = await session.execute(stmt)
        row = result.scalars().first()

        if not row:
            return {"error": f"User '{name} {surname}' not found"}
        
        log.info(f"Retrieved user {row.id}: {row.first_name} {row.last_name}, email: {row.email}")
        return {
            "id": row.id,
            "first_name": row.first_name,
            "last_name": row.last_name,
            "email": row.email,
            "customer_tier": row.customer_tier,
        }


@mcp.tool
async def customers_get_user_by_email(email: str) -> dict:
    """
    Find a customer by their email address.

    Use this tool when you have a customer's email and need to look up
    their profile.

    Args:
        email: The customer's registered email address.

    Returns:
        The matching user's profile, or an error if no user is found.
    """
    async with get_async_session() as session:
        stmt = select(User).where(func.lower(User.email) == email.lower())
        result = await session.execute(stmt)
        row = result.scalars().first()
        if not row:
            return {"error": f"User with email '{email}' not found"}
        
        log.info(f"Retrieved user {row.id}: {row.first_name} {row.last_name}, email: {row.email}")
        return {
            "id": row.id,
            "first_name": row.first_name,
            "last_name": row.last_name,
            "email": row.email,
            "customer_tier": row.customer_tier,
        }


@mcp.tool
async def customers_get_users_by_region(region: str) -> list[dict]:
    """
    Find customers by geographic location.

    Searches user records by city or country using a case-insensitive
    partial match.

    Args:
        region: Location keyword to search for.

    Examples:
        "India" -> users located in India
        "London" -> users located in London
        "York" -> matches "New York"

    Returns:
        List of matching users with profile and location information.
    """
    async with get_async_session() as session:
        pattern = f"%{region.lower()}%"
        stmt = select(User).where(
            func.lower(User.city).like(pattern) | func.lower(User.country).like(pattern)
        )
        result = await session.execute(stmt)
        users = result.scalars().all()

        log.info(f"Found {len(users)} users matching region '{region}'")
        return [
            {
                "id": u.id,
                "first_name": u.first_name,
                "last_name": u.last_name,
                "city": u.city,
                "country": u.country,
                "customer_tier": u.customer_tier,
            }
            for u in users
        ]


@mcp.tool
async def customers_get_users_by_spent(k: int) -> list[dict]:
    """
    Find the top customers by total spending.

    Use this tool when a user asks for the highest-value customers,
    biggest spenders, top buyers, or customer rankings based on
    purchase history.

    Args:
        k: Number of top customers to return.

    Returns:
        List of customers ranked by total amount spent across all orders,
        from highest spender to lowest.
    """
    async with get_async_session() as session:
        total = func.sum(Order.subtotal)
        stmt = (
            select(User.id, User.first_name, User.last_name, total.label("total_spent"))
            .join(Order, Order.user_id == User.id)
            .group_by(User.id, User.first_name, User.last_name)
            .order_by(total.desc())
            .limit(k)
        )
        result = await session.execute(stmt)

        log.info(f"Retrieved top {k} customers by total spent")
        return [
            {
                "id": r.id,
                "first_name": r.first_name,
                "last_name": r.last_name,
                "total_spent": float(r.total_spent),
            }
            for r in result.all()
        ]


@mcp.tool
async def customers_get_users_by_tier(tier: str) -> list[dict]:
    """Return all users belonging to the given customer tier (case-insensitive).

    Common tier values: new, casual, loyal, vip.
    Source: users table — filters on customer_tier column.
    """
    async with get_async_session() as session:
        stmt = select(User).where(func.lower(User.customer_tier) == tier.lower())
        result = await session.execute(stmt)
        users = result.scalars().all()

        log.info(f"Retrieved {len(users)} users in tier '{tier}'")
        return [
            {
                "id": u.id,
                "first_name": u.first_name,
                "last_name": u.last_name,
                "email": u.email,
                "customer_tier": u.customer_tier,
            }
            for u in users
        ]


@mcp.tool
async def customers_get_users_orders_analysis(user_id: int) -> dict:
    """Return an order analytics summary for a user.

    Includes: total_orders, status_breakdown (per-status count),
    total_spent, avg_order_value.
    Source: orders table — filters on user_id.
    """
    async with get_async_session() as session:
        stmt = select(Order).where(Order.user_id == user_id)
        result = await session.execute(stmt)
        orders = result.scalars().all()

        if not orders:
            return {"user_id": user_id, "total_orders": 0}

        status_breakdown: dict[str, int] = {}
        for o in orders:
            key = o.status.value if hasattr(o.status, "value") else str(o.status)
            status_breakdown[key] = status_breakdown.get(key, 0) + 1

        subtotals = [float(o.subtotal) for o in orders]
        total = sum(subtotals)

        log.info(f"Order analysis for user {user_id}:{len(orders)} orders,total spent ${total:.2f}")
        return {
            "user_id": user_id,
            "total_orders": len(orders),
            "status_breakdown": status_breakdown,
            "total_spent": round(total, 2),
            "avg_order_value": round(total / len(orders), 2),
        }


@mcp.tool
async def customers_get_user_review_on_product(user_id: int, product_id: int) -> list[dict]:
    """Return all reviews written by a user for a specific product.

    Source: reviews table — filters on user_id AND product_id.
    """
    async with get_async_session() as session:
        stmt = select(Review).where(
            Review.user_id == user_id,
            Review.product_id == product_id,
        )
        result = await session.execute(stmt)
        reviews = result.scalars().all()
        log.info(f"Retrieved {len(reviews)} reviews for user {user_id} on product {product_id}")
        return [
            {
                "id": r.id,
                "rating": r.rating,
                "title": r.title,
                "body": r.body,
                "verified_purchase": r.verified_purchase,
                "helpful_votes": r.helpful_votes,
                "reviewed_at": r.reviewed_at.isoformat() if r.reviewed_at else None,
            }
            for r in reviews
        ]
