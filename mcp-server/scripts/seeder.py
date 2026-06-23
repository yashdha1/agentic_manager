"""
Seed all dataset CSVs into PostgreSQL in FK-safe order.

Usage (from mcp-server/ directory):
    uv run python -m src.core.db.seeder           # create tables + insert
    uv run python -m src.core.db.seeder --reset   # truncate then re-insert

Prerequisites:
    1. PostgreSQL is running (docker compose up -d postgres)
    2. PG_ASYNC_URL and LANGSMITH_API_KEY are set in environment / .env
    3. CSVs exist in src/dataset/ (run generate_dataset.py first)
"""

import asyncio
import csv
import sys
from datetime import UTC, datetime, timezone
from decimal import Decimal
from pathlib import Path

# Ensure mcp-server/ root is on sys.path when run as a script
sys.path.insert(0, str(Path(__file__).parents[1]))

from sqlalchemy import insert, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from src.core.config import settings
from src.core.db.schemas import (
    Base,
    InventoryEvent,
    Order,
    OrderItem,
    Product,
    Refund,
    RefundStatus,
    Review,
    User,
)
from src.core.db.schemas.Orders import OrderStatus, PaymentStatus

DATASET_DIR = Path(__file__).parent.parent / "dataset"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read_csv(filename: str) -> list[dict]:
    path = DATASET_DIR / filename
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Run: uv run --group dev python scripts/generate_dataset.py"
        )
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _dt(s: str) -> datetime | None:
    if not s:
        return None
    dt = datetime.fromisoformat(s)
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def _dec(s) -> Decimal | None:
    if s == "" or s is None:
        return None
    return Decimal(str(s))


def _bool(s) -> bool:
    if isinstance(s, bool):
        return s
    return str(s).strip().lower() in ("true", "1", "yes")


def _int_or_none(s: str) -> int | None:
    if s == "" or s is None:
        return None
    return int(s)


# ---------------------------------------------------------------------------
# Table-specific loaders
# ---------------------------------------------------------------------------

def _load_users() -> list[dict]:
    return [
        {
            "id": int(r["id"]),
            "first_name": r["first_name"],
            "last_name": r["last_name"],
            "email": r["email"],
            "phone": r["phone"] or None,
            "country": r["country"] or None,
            "city": r["city"] or None,
            "postcode": r["postcode"] or None,
            "is_active": _bool(r["is_active"]),
            "customer_tier": r["customer_tier"] or None,
            "has_newsletter": _bool(r["has_newsletter"]),
            "created_at": _dt(r["created_at"]),
            "updated_at": _dt(r.get("updated_at", "")),
        }
        for r in _read_csv("users.csv")
    ]


def _load_products() -> list[dict]:
    return [
        {
            "id": int(r["id"]),
            "sku": r["sku"] or None,
            "name": r["name"],
            "description": r.get("description") or None,
            "category": r["category"] or None,
            "sub_category": r.get("sub_category") or None,
            "brand": r.get("brand") or None,
            "price": _dec(r["price"]),
            "cost_price": _dec(r.get("cost_price", "")) or None,
            "stock_quantity": int(r["stock_quantity"]),
            "is_active": _bool(r["is_active"]),
            "created_at": _dt(r["created_at"]),
            "updated_at": _dt(r.get("updated_at", "")),
        }
        for r in _read_csv("products.csv")
    ]


def _load_orders() -> list[dict]:
    status_map = {s.value: s for s in OrderStatus}
    payment_map = {s.value: s for s in PaymentStatus}

    return [
        {
            "id": int(r["id"]),
            "user_id": int(r["user_id"]),
            "status": status_map.get(r["order_status"], OrderStatus.PENDING),
            "subtotal": _dec(r["subtotal"]),
            "discount_amount": _dec(r["discount_amount"]) or Decimal("0"),
            "shipping_amount": _dec(r.get("shipping_amount", "0")) or Decimal("0"),
            "currency": r.get("currency") or None,
            "payment_method": r.get("payment_method") or None,
            "payment_status": payment_map.get(r["payment_status"], PaymentStatus.PENDING),
            "shipping_country": r.get("shipping_country") or None,
            "shipping_city": r.get("shipping_city") or None,
            "shipping_postcode": r.get("shipping_postcode") or None,
            "device_type": r.get("device_type") or None,
            "acquisition_channel": r.get("acquisition_channel") or None,
            "ordered_at": _dt(r["ordered_at"]),
            "delivered_at": _dt(r.get("delivered_at", "")),
            "cancelled_at": _dt(r.get("cancelled_at", "")),
            "policy_applied": None,
        }
        for r in _read_csv("orders.csv")
    ]


def _load_order_items() -> list[dict]:
    return [
        {
            "id": int(r["id"]),
            "order_id": int(r["order_id"]),
            "product_id": int(r["product_id"]),
            "quantity": int(r["quantity"]),
            "unit_price": _dec(r["unit_price"]),
        }
        for r in _read_csv("order_items.csv")
    ]


def _load_reviews() -> list[dict]:
    return [
        {
            "id": int(r["id"]),
            "order_id": _int_or_none(r.get("order_id", "")),
            "user_id": int(r["user_id"]),
            "product_id": int(r["product_id"]),
            "rating": int(r["rating"]),
            "title": r.get("title") or None,
            "body": r.get("body") or None,
            "verified_purchase": _bool(r.get("verified_purchase", "false")),
            "helpful_votes": int(r.get("helpful_votes") or 0),
            "flagged": _bool(r.get("flagged", "false")),
            "reviewed_at": _dt(r["reviewed_at"]),
            "updated_at": _dt(r.get("updated_at", "")),
        }
        for r in _read_csv("reviews.csv")
    ]


def _load_refunds() -> list[dict]:
    status_map = {s.value: s for s in RefundStatus}
    return [
        {
            "id": int(r["id"]),
            "order_id": int(r["order_id"]),
            "reason": r["reason"],
            "refund_amount": _dec(r["refund_amount"]),
            "status": status_map.get(r["status"], RefundStatus.PENDING),
            "processed_at": _dt(r.get("processed_at", "")),
        }
        for r in _read_csv("refunds.csv")
    ]


def _load_inventory_events() -> list[dict]:
    return [
        {
            "id": int(r["id"]),
            "product_id": int(r["product_id"]),
            "event_type": r["event_type"],
            "quantity_change": int(r["quantity_change"]),
            "new_stock_level": int(r["new_stock_level"]),
            "event_date": _dt(r["event_date"]),
            "notes": r.get("notes") or None,
        }
        for r in _read_csv("inventory_events.csv")
    ]


# ---------------------------------------------------------------------------
# Seeder
# ---------------------------------------------------------------------------

TRUNCATE_ORDER = [
    "inventory_events",
    "refunds",
    "reviews",
    "order_items",
    "orders",
    "products",
    "users",
]

_CHUNK = 500


def _chunks(lst: list, size: int):
    for i in range(0, len(lst), size):
        yield lst[i : i + size]


async def _bulk_insert(session, model, rows: list[dict], label: str) -> None:
    if not rows:
        print(f"  {label}: 0 rows (skipped)")
        return
    for chunk in _chunks(rows, _CHUNK):
        await session.execute(insert(model), chunk)
    print(f"  {label}: {len(rows)} rows inserted")


async def _reset_sequences(session) -> None:
    """Advance PostgreSQL serial sequences past the maximum explicitly-seeded IDs.

    Bulk inserts that supply explicit ``id`` values bypass the underlying
    sequences, leaving them at their initial value (usually 1).  Any
    subsequent INSERT that omits ``id`` (e.g. from HITL tools) would then
    attempt to reuse an already-taken primary key, causing a
    ``UniqueViolation`` constraint error.  This helper sets every affected
    sequence to ``MAX(id) + 1`` so that auto-generated IDs never collide
    with seeded data.
    """
    tables = [
        "users",
        "products",
        "orders",
        "order_items",
        "reviews",
        "refunds",
        "inventory_events",
    ]
    for table in tables:
        await session.execute(
            text(
                f"SELECT setval("
                f"pg_get_serial_sequence('{table}', 'id'), "
                f"COALESCE((SELECT MAX(id) FROM {table}), 0) + 1, "
                f"false)"
            )
        )
    print("Sequences reset.")


async def seed(reset: bool = False) -> None:
    engine = create_async_engine(settings.PG_ASYNC_URL, echo=False)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Tables ensured.")

    async with Session() as session:
        async with session.begin():
            if reset:
                print("Truncating tables...")
                for table in TRUNCATE_ORDER:
                    await session.execute(
                        text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE")
                    )

            print("Loading CSVs and inserting...")
            await _bulk_insert(session, User, _load_users(), "users")
            await _bulk_insert(session, Product, _load_products(), "products")
            await _bulk_insert(session, Order, _load_orders(), "orders")
            await _bulk_insert(session, OrderItem, _load_order_items(), "order_items")
            await _bulk_insert(session, Review, _load_reviews(), "reviews")
            await _bulk_insert(session, Refund, _load_refunds(), "refunds")
            await _bulk_insert(session, InventoryEvent, _load_inventory_events(), "inventory_events")

            print("Resetting sequences...")
            await _reset_sequences(session)

    await engine.dispose()
    print("\nSeeding complete.")


if __name__ == "__main__":
    asyncio.run(seed(reset="--reset" in sys.argv))
