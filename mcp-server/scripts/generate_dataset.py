import csv
import math
import random
import sys
from datetime import UTC, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.time_utils import random_past  # noqa: E402
from faker import Faker

SEED = 42
random.seed(SEED)
fake = Faker()
Faker.seed(SEED)

DATASET_DIR = Path(__file__).parent.parent / "src" / "dataset"
DATASET_DIR.mkdir(parents=True, exist_ok=True)

N_USERS = 500
N_PRODUCTS = 500
N_ORDERS = 2000
N_REVIEWS = 500
N_INVENTORY_EVENTS = 1000
N_TICKETS = 300

# ---------------------------------------------------------------------------
# Domain constants
# ---------------------------------------------------------------------------

COUNTRIES = ["United States", "United Kingdom", "France", "Germany", "Australia", "Canada", "Netherlands", "Spain"]

CURRENCY_BY_COUNTRY = {
    "United States": "USD",
    "United Kingdom": "GBP",
    "France": "EUR",
    "Germany": "EUR",
    "Australia": "AUD",
    "Canada": "CAD",
    "Netherlands": "EUR",
    "Spain": "EUR",
}

CITIES_BY_COUNTRY = {
    "United States": ["New York", "Los Angeles", "Chicago", "Houston", "Seattle", "Austin", "Boston"],
    "United Kingdom": ["London", "Manchester", "Birmingham", "Glasgow", "Edinburgh", "Bristol"],
    "France": ["Paris", "Lyon", "Marseille", "Toulouse", "Bordeaux", "Lille"],
    "Germany": ["Berlin", "Munich", "Hamburg", "Frankfurt", "Cologne", "Stuttgart"],
    "Australia": ["Sydney", "Melbourne", "Brisbane", "Perth", "Adelaide"],
    "Canada": ["Toronto", "Vancouver", "Montreal", "Calgary", "Ottawa"],
    "Netherlands": ["Amsterdam", "Rotterdam", "The Hague", "Utrecht", "Eindhoven"],
    "Spain": ["Madrid", "Barcelona", "Valencia", "Seville", "Bilbao"],
}

POSTCODE_FORMAT = {
    "United States": lambda: f"{random.randint(10000, 99999)}",
    "United Kingdom": lambda: f"{random.choice('ABCDEFGHJKLMNPRSTUVWXY')}{random.randint(1,9)} {random.randint(1,9)}{random.choice('ABCDEFGHJKLMNPRSTUVWXY')}{random.choice('ABCDEFGHJKLMNPRSTUVWXY')}",
    "France": lambda: f"{random.randint(10000, 99999)}",
    "Germany": lambda: f"{random.randint(10000, 99999)}",
    "Australia": lambda: f"{random.randint(2000, 9999)}",
    "Canada": lambda: f"{random.choice('ABCEGHJKLMNPRSTVXY')}{random.randint(0,9)}{random.choice('ABCEGHJKLMNPRSTVXY')} {random.randint(0,9)}{random.choice('ABCEGHJKLMNPRSTVXY')}{random.randint(0,9)}",
    "Netherlands": lambda: f"{random.randint(1000, 9999)} {random.choice('ABCDEFGHJKLMNPRSTUVWXYZ')}{random.choice('ABCDEFGHJKLMNPRSTUVWXYZ')}",
    "Spain": lambda: f"{random.randint(10000, 52999):05d}",
}

TIERS = ["new", "casual", "loyal", "vip"]
TIER_WEIGHTS = [0.55, 0.25, 0.15, 0.05]

PAYMENT_METHODS = ["card", "paypal", "apple_pay", "google_pay", "buy_now_pay_later"]
DEVICE_TYPES = ["desktop", "mobile", "tablet"]
DEVICE_WEIGHTS = [0.45, 0.40, 0.15]
ACQUISITION_CHANNELS = ["organic_search", "paid_search", "direct", "email", "social", "referral", "display_ads", "affiliate"]

ORDER_STATUSES = ["delivered", "cancelled", "returned", "processing", "shipped"]
ORDER_STATUS_WEIGHTS = [0.55, 0.20, 0.10, 0.10, 0.05]

REFUND_REASONS = [
    "item_not_as_described",
    "damaged_on_arrival",
    "wrong_item_sent",
    "changed_mind",
    "late_delivery",
    "size_or_fit_issue",
]

INVENTORY_NOTE_BY_TYPE = {
    "sale_deduction": [
        "Customer order fulfilled",
        "Online sale processed",
        "Order dispatched",
    ],
    "restock": [
        "Supplier delivery received",
        "Emergency restock due to high demand",
        "Bulk import - quarterly stock review",
        "Warehouse transfer in",
        "Return to stock - quality check passed",
    ],
    "adjustment": [
        "Stock count correction",
        "System reconciliation",
        "Shrinkage adjustment",
        "Damaged units written off",
        "Audit correction",
    ],
}

# Category → list of (sub_category, brand_prefix, sku_prefix)
CATEGORY_CONFIG = {
    "Sports": [
        ("Fitness", "IronPath", "SF"),
        ("Outdoor", "TrailForce", "SO"),
        ("Cycling", "VeloEdge", "SC"),
    ],
    "Electronics": [
        ("Smart Home", "NexLink", "ESH"),
        ("Headphones", "Auraloop", "EH"),
        ("Laptops", "Voltix", "EL"),
        ("Cameras", "OpticPro", "EC"),
    ],
    "Home": [
        ("Kitchen", "ChefMate", "HK"),
        ("Decor", "Serein Lab", "HD"),
        ("Furniture", "NestCraft", "HF"),
    ],
    "Beauty": [
        ("Skincare", "Velvet Hue", "BS"),
        ("Makeup", "Lumiere Co", "BM"),
        ("Haircare", "GlossGlow", "BH"),
    ],
    "Toys": [
        ("Learning Toys", "BrightMind", "TL"),
        ("Outdoor Play", "PlayZone", "TO"),
        ("Board Games", "GameCraft", "TBG"),
    ],
    "Fashion": [
        ("Footwear", "StepUp", "FF"),
        ("Women's Apparel", "Fiorelux", "FWA"),
        ("Men's Apparel", "DapperCo", "FMA"),
        ("Accessories", "CharmWear", "FA"),
    ],
    "Food & Drink": [
        ("Supplements", "PureBoost", "FDS"),
        ("Coffee & Tea", "BrewRoots", "FDCT"),
        ("Snacks", "MunchCo", "FDSN"),
    ],
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _round2(v: float) -> float:
    return float(Decimal(str(v)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def write_csv(filename: str, rows: list[dict], fieldnames: list[str]) -> None:
    path = DATASET_DIR / filename
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"  wrote {len(rows):>6} rows -> {path.name}")


# ---------------------------------------------------------------------------
# Generators
# ---------------------------------------------------------------------------

def generate_users(n: int) -> list[dict]:
    rows = []

    for i in range(1, n + 1):
        tier = random.choices(TIERS, weights=TIER_WEIGHTS)[0]
        country = random.choice(COUNTRIES)
        city = random.choice(CITIES_BY_COUNTRY[country])
        postcode = POSTCODE_FORMAT[country]()
        created_at = random_past(30)

        if tier == "new":
            total_spent = _round2(random.uniform(0, 150))
        elif tier == "casual":
            total_spent = _round2(random.uniform(100, 2000))
        elif tier == "loyal":
            total_spent = _round2(random.uniform(1500, 10000))
        else:  # vip
            total_spent = _round2(random.uniform(8000, 60000))

        has_newsletter = random.random() < (0.3 if tier == "new" else 0.6)

        rows.append({
            "id": i,
            "first_name": fake.first_name(),
            "last_name": fake.last_name(),
            "email": fake.unique.email(),
            "phone": fake.phone_number()[:20] if random.random() > 0.05 else "",
            "country": country,
            "city": city,
            "postcode": postcode,
            "is_active": random.random() > 0.03,
            "customer_tier": tier,
            "total_spent": total_spent,
            "has_newsletter": has_newsletter,
            "created_at": created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "updated_at": "",
        })
    return rows


def generate_products(n: int) -> list[dict]:
    rows = []
    categories = list(CATEGORY_CONFIG.keys())
    sku_counters: dict[str, int] = {}

    # Price ranges by category
    price_range = {
        "Sports": (15, 400),
        "Electronics": (25, 1200),
        "Home": (10, 600),
        "Beauty": (8, 150),
        "Toys": (10, 200),
        "Fashion": (20, 500),
        "Food & Drink": (5, 80),
    }

    for i in range(1, n + 1):
        category = random.choice(categories)
        sub_cat, brand, sku_prefix = random.choice(CATEGORY_CONFIG[category])
        counter = sku_counters.get(sku_prefix, 0) + 1
        sku_counters[sku_prefix] = counter
        sku = f"{sku_prefix}-{counter:05d}-{random.randint(10, 99)}"

        lo, hi = price_range[category]
        price = _round2(random.uniform(lo, hi))
        cost_price = _round2(price * random.uniform(0.30, 0.65))
        stock = random.randint(0, 5000)
        is_active = random.random() > 0.05

        # Product names: brand + descriptive noun
        nouns = {
            "Sports": ["Pro Bar", "Resistance Band Set", "Yoga Mat", "Kettlebell", "Jump Rope", "Pull-Up Bar", "Water Bottle"],
            "Electronics": ["Smart Speaker", "Wireless Earbuds", "4K Webcam", "USB-C Hub", "Smart Doorbell", "LED Strip", "Portable Charger"],
            "Home": ["Air Fryer", "Coffee Maker", "Throw Pillow Set", "Scented Candle", "Storage Basket", "Wall Clock", "Desk Lamp"],
            "Beauty": ["Vitamin C Serum", "Moisturiser SPF30", "Foundation Kit", "Lip Palette", "Hair Mask", "Dry Shampoo", "Eye Cream"],
            "Toys": ["Building Blocks", "Puzzle Set", "Science Kit", "Remote Car", "Plush Bear", "Card Game", "Magnetic Tiles"],
            "Fashion": ["Running Shoes", "Casual Sneakers", "Linen Shirt", "Wool Coat", "Leather Belt", "Tote Bag", "Baseball Cap"],
            "Food & Drink": ["Whey Protein", "Collagen Powder", "Cold Brew Blend", "Herbal Tea Box", "Granola Mix", "Energy Gummies", "Vitamin D Drops"],
        }
        name = f"{brand} {random.choice(nouns[category])}"

        rows.append({
            "id": i,
            "sku": sku,
            "name": name,
            "description": f"Premium {sub_cat.lower()} product by {brand}. High quality and durable.",
            "category": category,
            "sub_category": sub_cat,
            "brand": brand,
            "price": price,
            "cost_price": cost_price,
            "stock_quantity": stock,
            "is_active": is_active,
            "created_at": random_past(30).strftime("%Y-%m-%d %H:%M:%S"),
            "updated_at": "",
        })
    return rows


def generate_orders(users: list[dict], n: int) -> list[dict]:
    rows = []

    # Weight users by tier so vip/loyal get more orders
    tier_order_weight = {"new": 1, "casual": 3, "loyal": 6, "vip": 10}
    weights = [tier_order_weight[u["customer_tier"]] for u in users]
    total_w = sum(weights)
    norm_weights = [w / total_w for w in weights]

    for i in range(1, n + 1):
        user = random.choices(users, weights=norm_weights)[0]
        ordered_at = random_past(30)
        country = user["country"]
        currency = CURRENCY_BY_COUNTRY[country]

        status = random.choices(ORDER_STATUSES, weights=ORDER_STATUS_WEIGHTS)[0]
        payment_method = random.choice(PAYMENT_METHODS)

        if status in ("cancelled",):
            subtotal = 0.0
            discount = 0.0
            shipping = 0.0
            total = 0.0
            payment_status = random.choice(["failed", "pending"])
            delivered_at = ""
            cancelled_at = (ordered_at + timedelta(hours=random.randint(1, 48))).strftime("%Y-%m-%d %H:%M:%S")
        elif status == "returned":
            subtotal = _round2(random.uniform(15, 800))
            discount = _round2(subtotal * random.uniform(0, 0.20))
            shipping = _round2(random.uniform(0, 20))
            total = _round2(subtotal - discount + shipping)
            payment_status = "refunded"
            delivered_at = (ordered_at + timedelta(days=random.randint(2, 10))).strftime("%Y-%m-%d %H:%M:%S")
            cancelled_at = ""
        else:
            subtotal = _round2(random.uniform(15, 2000))
            discount = _round2(subtotal * random.uniform(0, 0.25))
            shipping = _round2(random.uniform(0, 30) if subtotal > 50 else random.uniform(5, 30))
            total = _round2(subtotal - discount + shipping)
            if status == "delivered":
                payment_status = "paid"
                delivered_at = (ordered_at + timedelta(days=random.randint(2, 14))).strftime("%Y-%m-%d %H:%M:%S")
            else:
                payment_status = random.choices(["paid", "pending"], weights=[0.8, 0.2])[0]
                delivered_at = ""
            cancelled_at = ""

        # Shipping address: 90% same as user, 10% different
        if random.random() < 0.9:
            ship_country = country
            ship_city = user["city"]
            ship_postcode = user["postcode"]
        else:
            ship_country = random.choice(COUNTRIES)
            ship_city = random.choice(CITIES_BY_COUNTRY[ship_country])
            ship_postcode = POSTCODE_FORMAT[ship_country]()

        rows.append({
            "id": i,
            "user_id": user["id"],
            "order_status": status,
            "payment_status": payment_status,
            "payment_method": payment_method,
            "currency": currency,
            "subtotal": subtotal,
            "discount_amount": discount,
            "shipping_amount": shipping,
            "total_amount": total,
            "shipping_country": ship_country,
            "shipping_city": ship_city,
            "shipping_postcode": ship_postcode,
            "device_type": random.choices(DEVICE_TYPES, weights=DEVICE_WEIGHTS)[0],
            "acquisition_channel": random.choice(ACQUISITION_CHANNELS),
            "ordered_at": ordered_at.strftime("%Y-%m-%d %H:%M:%S"),
            "delivered_at": delivered_at,
            "cancelled_at": cancelled_at,
        })
    return rows


def generate_order_items(orders: list[dict], products: list[dict]) -> list[dict]:
    rows = []
    active_products = [p for p in products if p["is_active"]]
    item_id = 1

    for order in orders:
        if order["order_status"] == "cancelled":
            # Cancelled orders still get an item record (0 quantity)
            product = random.choice(active_products)
            rows.append({
                "id": item_id,
                "order_id": order["id"],
                "product_id": product["id"],
                "quantity": 0,
                "unit_price": 0.0,
                "line_total": 0.0,
            })
        else:
            product = random.choice(active_products)
            unit_price = float(product["price"])
            qty = random.randint(1, 3)
            line_total = _round2(unit_price * qty)
            rows.append({
                "id": item_id,
                "order_id": order["id"],
                "product_id": product["id"],
                "quantity": qty,
                "unit_price": unit_price,
                "line_total": line_total,
            })
        item_id += 1
    return rows


def generate_reviews(
    orders: list[dict],
    order_items: list[dict],
    n: int,
) -> list[dict]:
    eligible = [o for o in orders if o["order_status"] in ("delivered", "returned")]
    if not eligible:
        return []

    # Build order_id → product_id lookup from order_items
    oi_by_order = {oi["order_id"]: oi for oi in order_items}

    sample_size = min(n, len(eligible))
    sampled = random.sample(eligible, sample_size)

    # Rating distribution: skewed toward positive
    rating_weights = [2, 4, 10, 25, 59]  # 1-star to 5-star

    review_titles = {
        5: ["Superb", "Absolutely love it", "Best purchase ever", "Highly recommend", "Exceeded expectations", "Fantastic quality"],
        4: ["Very good", "Really happy with this", "Great value", "Solid product", "Mostly great", "Good buy"],
        3: ["Decent", "It's ok", "Average", "Could be better", "Not bad", "Mixed feelings"],
        2: ["Disappointed", "Not what I expected", "Would not repurchase", "Some issues", "Below average"],
        1: ["Very poor quality", "Complete waste of money", "Avoid", "Terrible experience", "Broken on arrival"],
    }
    review_bodies = {
        5: [
            "Fantastic. Does exactly what it says on the tin.",
            "Really impressed by the build quality. Will buy again.",
            "Fast delivery, great packaging, excellent product.",
            "My whole family loves it. Worth every penny.",
        ],
        4: [
            "Good product overall, minor room for improvement.",
            "Works as described. Happy with the purchase.",
            "Solid quality, delivery was quick.",
            "Meets expectations, packaging was good.",
        ],
        3: [
            "It's okay but nothing special.",
            "Does the job but feels a bit cheap.",
            "Average quality for the price.",
            "Some features work well, others not so much.",
        ],
        2: [
            "Not quite what I expected from the photos.",
            "Quality feels cheaper than described.",
            "Had minor issues, customer service was slow.",
            "Would not buy again at this price.",
        ],
        1: [
            "Arrived damaged and poorly packaged.",
            "Completely different from the description.",
            "Broke within a week of use.",
            "Would not recommend to anyone.",
        ],
    }

    rows = []
    for review_id, order in enumerate(sampled, start=1):
        rating = random.choices([1, 2, 3, 4, 5], weights=rating_weights)[0]
        oi = oi_by_order.get(order["id"])
        product_id = oi["product_id"] if oi else 1

        ordered_at = datetime.fromisoformat(order["ordered_at"]).replace(tzinfo=UTC)
        reviewed_at = ordered_at + timedelta(days=random.randint(3, 60))

        rows.append({
            "id": review_id,
            "order_id": order["id"],
            "user_id": order["user_id"],
            "product_id": product_id,
            "rating": rating,
            "title": random.choice(review_titles[rating]),
            "body": random.choice(review_bodies[rating]),
            "verified_purchase": True,
            "helpful_votes": int(random.expovariate(0.3)) if random.random() > 0.3 else 0,
            "flagged": random.random() < 0.02,
            "reviewed_at": reviewed_at.strftime("%Y-%m-%d %H:%M:%S"),
            "updated_at": "",
        })
    return rows


def generate_refunds(orders: list[dict]) -> list[dict]:
    eligible = [o for o in orders if o["payment_status"] == "refunded"]
    rows = []

    for refund_id, order in enumerate(eligible, start=1):
        total = float(order["total_amount"]) if order["total_amount"] else 0.0
        refund_amount = _round2(total * random.uniform(0.5, 1.0)) if total > 0 else _round2(random.uniform(10, 100))
        status = random.choices(["approved", "pending", "rejected"], weights=[0.75, 0.18, 0.07])[0]
        ordered_at = datetime.fromisoformat(order["ordered_at"]).replace(tzinfo=UTC)
        processed_at = ordered_at + timedelta(days=random.randint(1, 14))

        rows.append({
            "id": refund_id,
            "order_id": order["id"],
            "reason": random.choice(REFUND_REASONS),
            "refund_amount": refund_amount,
            "status": status,
            "processed_at": processed_at.strftime("%Y-%m-%d %H:%M:%S") if status != "pending" else "",
        })
    return rows


def generate_inventory_events(
    products: list[dict],
    order_items: list[dict],
    n: int,
) -> list[dict]:
    rows = []
    event_id = 1

    # Track running stock levels
    stock_levels = {p["id"]: int(p["stock_quantity"]) for p in products}

    # Sale deductions from delivered order items (up to n//2)
    delivered_items = [oi for oi in order_items if oi["quantity"] > 0]
    sale_sample = min(len(delivered_items), n // 2)
    for oi in random.sample(delivered_items, sale_sample):
        pid = oi["product_id"]
        qty = oi["quantity"]
        new_level = max(0, stock_levels[pid] - qty)
        stock_levels[pid] = new_level
        rows.append({
            "id": event_id,
            "product_id": pid,
            "event_type": "sale_deduction",
            "quantity_change": -qty,
            "new_stock_level": new_level,
            "event_date": random_past(30).strftime("%Y-%m-%d %H:%M:%S"),
            "notes": random.choice(INVENTORY_NOTE_BY_TYPE["sale_deduction"]),
        })
        event_id += 1

    # Fill remaining events with restocks and adjustments
    remaining = n - len(rows)
    for _ in range(remaining):
        product = random.choice(products)
        pid = product["id"]
        event_type = random.choices(["restock", "adjustment"], weights=[0.65, 0.35])[0]

        if event_type == "restock":
            qty = random.randint(50, 500)
            new_level = stock_levels[pid] + qty
        else:
            qty = random.randint(-30, 30)
            new_level = max(0, stock_levels[pid] + qty)
            qty = new_level - stock_levels[pid]

        stock_levels[pid] = new_level
        rows.append({
            "id": event_id,
            "product_id": pid,
            "event_type": event_type,
            "quantity_change": qty,
            "new_stock_level": new_level,
            "event_date": random_past(30).strftime("%Y-%m-%d %H:%M:%S"),
            "notes": random.choice(INVENTORY_NOTE_BY_TYPE[event_type]),
        })
        event_id += 1

    # Sort by date for readability
    rows.sort(key=lambda r: r["event_date"])
    for idx, r in enumerate(rows, start=1):
        r["id"] = idx

    return rows


def generate_policies() -> list[dict]:
    rows = []
    for i, ptype in enumerate(POLICY_TYPES, start=1):
        effective_at = random_past(30)
        rows.append({
            "id": i,
            "policy_type": ptype,
            "title": ptype.replace("_", " ").title() + " Policy",
            "content": POLICY_CONTENT[ptype],
            "is_active": True,
            "effective_at": effective_at.strftime("%Y-%m-%d %H:%M:%S"),
            "expires_at": "",
            "created_at": effective_at.strftime("%Y-%m-%d %H:%M:%S"),
        })
    return rows


# ---------------------------------------------------------------------------
# Field name definitions (must match ORM columns exactly)
# ---------------------------------------------------------------------------

USER_FIELDS = ["id", "first_name", "last_name", "email", "phone", "country", "city", "postcode",
               "is_active", "customer_tier", "total_spent", "has_newsletter", "created_at", "updated_at"]

PRODUCT_FIELDS = ["id", "sku", "name", "description", "category", "sub_category", "brand",
                  "price", "cost_price", "stock_quantity", "is_active", "created_at", "updated_at"]

ORDER_FIELDS = ["id", "user_id", "order_status", "payment_status", "payment_method", "currency",
                "subtotal", "discount_amount", "shipping_amount", "total_amount",
                "shipping_country", "shipping_city", "shipping_postcode",
                "device_type", "acquisition_channel", "ordered_at", "delivered_at", "cancelled_at"]

ORDER_ITEM_FIELDS = ["id", "order_id", "product_id", "quantity", "unit_price", "line_total"]

REVIEW_FIELDS = ["id", "order_id", "user_id", "product_id", "rating", "title", "body",
                 "verified_purchase", "helpful_votes", "flagged", "reviewed_at", "updated_at"]

REFUND_FIELDS = ["id", "order_id", "reason", "refund_amount", "status", "processed_at"]

INVENTORY_FIELDS = ["id", "product_id", "event_type", "quantity_change", "new_stock_level", "event_date", "notes"]

POLICY_FIELDS = ["id", "policy_type", "title", "content", "is_active", "effective_at", "expires_at", "created_at"]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("Generating dataset...")

    users = generate_users(N_USERS)
    print(f"  users: {len(users)}")

    products = generate_products(N_PRODUCTS)
    print(f"  products: {len(products)}")

    orders = generate_orders(users, N_ORDERS)
    print(f"  orders: {len(orders)}")

    order_items = generate_order_items(orders, products)
    print(f"  order_items: {len(order_items)}")

    reviews = generate_reviews(orders, order_items, N_REVIEWS)
    print(f"  reviews: {len(reviews)}")

    refunds = generate_refunds(orders)
    print(f"  refunds: {len(refunds)}")

    inventory_events = generate_inventory_events(products, order_items, N_INVENTORY_EVENTS)
    print(f"  inventory_events: {len(inventory_events)}")

    policies = generate_policies()
    print(f"  policies: {len(policies)}")

    print("\nWriting CSVs...")
    write_csv("users.csv", users, USER_FIELDS)
    write_csv("products.csv", products, PRODUCT_FIELDS)
    write_csv("orders.csv", orders, ORDER_FIELDS)
    write_csv("order_items.csv", order_items, ORDER_ITEM_FIELDS)
    write_csv("reviews.csv", reviews, REVIEW_FIELDS)
    write_csv("refunds.csv", refunds, REFUND_FIELDS)
    write_csv("inventory_events.csv", inventory_events, INVENTORY_FIELDS)
    write_csv("policies.csv", policies, POLICY_FIELDS)

    print("\nDone. Run the seeder next:")
    print("  uv run python -m src.core.db.seeder")


if __name__ == "__main__":
    main()
