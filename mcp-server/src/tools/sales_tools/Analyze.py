from datetime import timedelta
from statistics import mean, median, pstdev

from core.db.pg_engine import get_async_session
from core.db.schemas import Order, OrderItem, OrderStatus, PaymentStatus, Product, Refund, Review
from core.logger import logger as log
from core.time_utils import now
from fastmcp import FastMCP
from sqlalchemy import and_, case, func, select, text

from .helpers import _as_float, _date_window, _normalize_enum

mcp = FastMCP("ecomm_mcp_sales_analysis")


@mcp.tool
async def sales_analyze_product_sales_time(
    start_date: str,
    end_date: str,
    compare_previous_period: bool = False,
) -> dict:
    """
    Return revenue, order count, and AOV for a date range.

    Args:
            start_date: Inclusive start date in ISO format (YYYY-MM-DD).
            end_date: Inclusive end date in ISO format (YYYY-MM-DD).
            compare_previous_period: If True, also compute metrics for 
            previous period of same length.

    Returns:
            Sales summary for requested period and optional previous period comparison.
    """
    try:
        start, end = _date_window(start_date, end_date)
        paid_statuses = [
            PaymentStatus.PAID,
            PaymentStatus.PARTIALLY_REFUNDED,
            PaymentStatus.REFUNDED,
        ]
        valid_order_status = [
            OrderStatus.CONFIRMED,
            OrderStatus.SHIPPED,
            OrderStatus.DELIVERED,
            OrderStatus.RETURNED,
        ]

        async with get_async_session() as session:
            revenue_expr = func.sum(OrderItem.quantity * OrderItem.unit_price)
            stmt = (
                select(
                    func.count(func.distinct(Order.id)).label("orders"),
                    func.sum(OrderItem.quantity).label("units"),
                    revenue_expr.label("revenue"),
                )
                .select_from(Order)
                .join(OrderItem, OrderItem.order_id == Order.id)
                .where(
                    and_(
                        Order.ordered_at >= start,
                        Order.ordered_at < end,
                        Order.payment_status.in_(paid_statuses),
                        Order.status.in_(valid_order_status),
                    )
                )
            )
            result = await session.execute(stmt)
            row = result.one()

            revenue = _as_float(row.revenue)
            orders = int(row.orders or 0)
            units = int(row.units or 0)

            payload: dict[str, float | int | str | dict] = {
                "start_date": start_date,
                "end_date": end_date,
                "orders": orders,
                "units": units,
                "revenue": round(revenue, 2),
                "aov": round((revenue / orders) if orders else 0.0, 2),
            }

            if compare_previous_period:
                delta = end - start
                prev_start = start - delta
                prev_end = start

                prev_stmt = (
                    select(
                        func.count(func.distinct(Order.id)).label("orders"),
                        func.sum(OrderItem.quantity).label("units"),
                        revenue_expr.label("revenue"),
                    )
                    .select_from(Order)
                    .join(OrderItem, OrderItem.order_id == Order.id)
                    .where(
                        and_(
                            Order.ordered_at >= prev_start,
                            Order.ordered_at < prev_end,
                            Order.payment_status.in_(paid_statuses),
                            Order.status.in_(valid_order_status),
                        )
                    )
                )
                prev_row = (await session.execute(prev_stmt)).one()
                prev_revenue = _as_float(prev_row.revenue)
                prev_orders = int(prev_row.orders or 0)
                prev_units = int(prev_row.units or 0)
                prev_aov = (prev_revenue / prev_orders) if prev_orders else 0.0

                payload["previous_period"] = {
                    "start_date": prev_start.date().isoformat(),
                    "end_date": (prev_end - timedelta(days=1)).date().isoformat(),
                    "orders": prev_orders,
                    "units": prev_units,
                    "revenue": round(prev_revenue, 2),
                    "aov": round(prev_aov, 2),
                }
                payload["delta"] = {
                    "orders": orders - prev_orders,
                    "units": units - prev_units,
                    "revenue": round(revenue - prev_revenue, 2),
                    "aov": round(((revenue / orders) if orders else 0.0) - prev_aov, 2),
                }

            log.info(f"Retrieved sales time summary for {start_date}..{end_date}")
            return payload
    except Exception as e:
        log.exception(f"Error in sales_analyze_product_sales_time: {e}")
        return {"error": str(e)}


@mcp.tool
async def sales_analyze_product_margin(
    product_id: int | None = None,
    limit: int = 20,
) -> list[dict]:
    """
    Return product margin metrics, optionally for one product.

    Args:
            product_id: Optional product ID filter.
            limit: Maximum rows for multi-product mode.

    Returns:
            Margin, markup, and estimated gross profit based on sold units.
    """
    try:
        async with get_async_session() as session:
            units_expr = func.coalesce(func.sum(OrderItem.quantity), 0).label("units_sold")
            stmt = (
                select(
                    Product.id,
                    Product.sku,
                    Product.name,
                    Product.price,
                    Product.cost_price,
                    units_expr,
                )
                .select_from(Product)
                .outerjoin(OrderItem, OrderItem.product_id == Product.id)
                .group_by(
                    Product.id,
                    Product.sku,
                    Product.name,
                    Product.price,
                    Product.cost_price,
                )
            )
            if product_id is not None:
                stmt = stmt.where(Product.id == product_id)
            else:
                stmt = stmt.limit(max(1, limit))

            rows = (await session.execute(stmt)).all()
            if product_id is None and rows:
                total_price = sum(_as_float(r.price) for r in rows)
                total_cost = sum(_as_float(r.cost_price) for r in rows)
                total_units = sum(int(r.units_sold or 0) for r in rows)
                avg_price = total_price / len(rows)
                avg_cost = total_cost / len(rows)
                margin_value = avg_price - avg_cost
                margin_pct = ((margin_value / avg_price) * 100.0) if avg_price > 0 else 0.0
                markup_pct = ((margin_value / avg_cost) * 100.0) if avg_cost > 0 else 0.0
                return [
                    {
                        "product_id": None,
                        "sku": None,
                        "name": "ALL PRODUCTS (aggregate)",
                        "price": round(avg_price, 2),
                        "cost_price": round(avg_cost, 2),
                        "margin_value": round(margin_value, 2),
                        "margin_pct": round(margin_pct, 2),
                        "markup_pct": round(markup_pct, 2),
                        "units_sold": total_units,
                        "estimated_gross_profit": round(margin_value * total_units, 2),
                    }
                ]
            output: list[dict] = []
            for r in rows:
                price = _as_float(r.price)
                cost = _as_float(r.cost_price)
                units = int(r.units_sold or 0)
                margin_value = price - cost
                margin_pct = ((margin_value / price) * 100.0) if price > 0 else 0.0
                markup_pct = ((margin_value / cost) * 100.0) if cost > 0 else 0.0
                gross_profit = margin_value * units

                output.append(
                    {
                        "product_id": r.id,
                        "sku": r.sku,
                        "name": r.name,
                        "price": round(price, 2),
                        "cost_price": round(cost, 2),
                        "margin_value": round(margin_value, 2),
                        "margin_pct": round(margin_pct, 2),
                        "markup_pct": round(markup_pct, 2),
                        "units_sold": units,
                        "estimated_gross_profit": round(gross_profit, 2),
                    }
                )

            if product_id is None:
                output.sort(key=lambda x: x["margin_pct"], reverse=True)

            log.info(
                "Retrieved product margin metrics"
                + (f" for product_id={product_id}" if product_id is not None else "")
            )
            return output
    except Exception as e:
        log.exception(f"Error in get_product_margin: {e}")
        return [{"error": str(e)}]


@mcp.tool
async def sales_analyze_product_health(product_id: int, lookback_days: int = 30) -> dict:
    """
    Return a compact health analysis for a product.

    Args:
            product_id: Product ID to analyze.
            lookback_days: Number of trailing days for sales/review/refund metrics.

    Returns:
            Health score plus supporting metrics.
    """
    try:
        end = now()
        start = end - timedelta(days=max(1, lookback_days))

        async with get_async_session() as session:
            product = await session.get(Product, product_id)
            if not product:
                return {"error": f"Product {product_id} not found"}

            sales_stmt = (
                select(
                    func.sum(OrderItem.quantity).label("units"),
                    func.sum(OrderItem.quantity * OrderItem.unit_price).label("revenue"),
                    func.count(func.distinct(Order.id)).label("orders"),
                )
                .select_from(OrderItem)
                .join(Order, Order.id == OrderItem.order_id)
                .where(
                    and_(
                        OrderItem.product_id == product_id,
                        Order.ordered_at >= start,
                        Order.ordered_at < end,
                    )
                )
            )
            sales = (await session.execute(sales_stmt)).one()

            review_stmt = select(
                func.avg(Review.rating).label("avg_rating"),
                func.count(Review.id).label("review_count"),
            ).where(and_(Review.product_id == product_id, Review.reviewed_at >= start))
            review = (await session.execute(review_stmt)).one()

            refund_stmt = (
                select(func.count(func.distinct(Refund.id)).label("refunds"))
                .select_from(Refund)
                .join(Order, Order.id == Refund.order_id)
                .join(OrderItem, OrderItem.order_id == Order.id)
                .where(
                    and_(
                        OrderItem.product_id == product_id,
                        Order.ordered_at >= start,
                        Order.ordered_at < end,
                    )
                )
            )
            refund = (await session.execute(refund_stmt)).one()

            units = int(sales.units or 0)
            orders = int(sales.orders or 0)
            revenue = _as_float(sales.revenue)
            avg_rating = float(review.avg_rating or 0.0)
            review_count = int(review.review_count or 0)
            refunds = int(refund.refunds or 0)

            refund_rate = (refunds / orders) if orders else 0.0
            sales_velocity = units / max(1, lookback_days)
            stock_days = (product.stock_quantity / sales_velocity) if sales_velocity > 0 else None

            # Score scale: 0-100
            rating_score = min(100.0, (avg_rating / 5.0) * 100.0)
            refund_score = max(0.0, 100.0 - (refund_rate * 100.0))
            stock_score = 50.0 if stock_days is None else max(0.0, min(100.0, stock_days))
            health_score = round(
                (0.5 * rating_score) + (0.3 * refund_score) + (0.2 * stock_score),
                2,
            )

            payload = {
                "product_id": product.id,
                "sku": product.sku,
                "name": product.name,
                "lookback_days": lookback_days,
                "metrics": {
                    "units_sold": units,
                    "orders": orders,
                    "revenue": round(revenue, 2),
                    "avg_rating": round(avg_rating, 2),
                    "review_count": review_count,
                    "refund_count": refunds,
                    "refund_rate": round(refund_rate, 4),
                    "stock_quantity": product.stock_quantity,
                    "stock_coverage_days": round(stock_days, 2) if stock_days is not None else None,
                },
                "health_score": health_score,
            }
            log.info(f"Computed product health for product_id={product_id}")
            return payload
    except Exception as e:
        log.exception(f"Error in sales_get_product_health: {e}")
        return {"error": str(e)}


@mcp.tool
async def sales_analyze_products_stats() -> dict:
    """
    Return high-level catalog stats.
    from the Products table.

    Returns:
            Product count, active/inactive split, category 
            count, brand count and price range summary.
    """
    try:
        async with get_async_session() as session:
            stmt = select(
                func.count(Product.id).label("total_products"),
                func.sum(case((Product.is_active.is_(True), 1), else_=0)).label("active_products"),
                func.sum(case((Product.is_active.is_(False), 1), else_=0)).label(
                    "inactive_products"
                ),
                func.count(func.distinct(Product.category)).label("total_categories"),
                func.count(func.distinct(Product.brand)).label("total_brands"),
                func.avg(Product.price).label("avg_price"),
                func.min(Product.price).label("min_price"),
                func.max(Product.price).label("max_price"),
            )
            result = await session.execute(stmt)
            row = result.one()
            payload = {
                "total_products": row.total_products or 0,
                "active_products": row.active_products or 0,
                "inactive_products": row.inactive_products or 0,
                "total_categories": row.total_categories or 0,
                "total_brands": row.total_brands or 0,
                "avg_price": round(_as_float(row.avg_price), 2),
                "min_price": _as_float(row.min_price),
                "max_price": _as_float(row.max_price),
            }
            log.info("Retrieved catalog stats")
            return payload
    except Exception as e:
        log.exception(f"Error in get_products_stats: {e}")
        return {"error": str(e)}


@mcp.tool
async def sales_analyze_anamoly(lookback_days: int = 30) -> dict:
    """
    Return simple daily anomaly detection for order volume and revenue.

    Args:
            lookback_days: Number of trailing days to evaluate.

    Returns:
            Detected anomaly days with z-score style context.
    """
    try:
        end = now()
        start = end - timedelta(days=max(7, lookback_days))

        async with get_async_session() as session:
            stmt = (
                select(
                    func.date_trunc(text("'day'"), Order.ordered_at).label("day"),
                    func.count(func.distinct(Order.id)).label("orders"),
                    func.coalesce(
                        func.sum(OrderItem.quantity * OrderItem.unit_price),
                        0,
                    ).label("revenue"),
                )
                .select_from(Order)
                .join(OrderItem, OrderItem.order_id == Order.id)
                .where(and_(Order.ordered_at >= start, Order.ordered_at < end))
                .group_by(text("date_trunc('day', orders.ordered_at)"))
                .order_by(text("date_trunc('day', orders.ordered_at) ASC"))
            )
            rows = (await session.execute(stmt)).all()

            if len(rows) < 2:
                return {
                    "lookback_days": lookback_days,
                    "message": "Not enough daily data to run anomaly metrics",
                    "series_days": len(rows),
                    "anomalies": [],
                }

            order_values = [int(r.orders or 0) for r in rows]
            revenue_values = [_as_float(r.revenue) for r in rows]

            orders_mean = mean(order_values)
            orders_std = pstdev(order_values)
            orders_median = median(order_values)
            orders_mad = median([abs(v - orders_median) for v in order_values])
            revenue_mean = mean(revenue_values)
            revenue_std = pstdev(revenue_values)
            revenue_median = median(revenue_values)
            revenue_mad = median([abs(v - revenue_median) for v in revenue_values])

            def _z_score(value: float, avg: float, std: float) -> float:
                if std == 0:
                    return 0.0
                return (value - avg) / std

            def _modified_z_score(value: float, med: float, mad: float) -> float:
                if mad == 0:
                    return 0.0
                return 0.6745 * ((value - med) / mad)

            anomalies: list[dict] = []
            for r in rows:
                orders_val = int(r.orders or 0)
                revenue_val = _as_float(r.revenue)

                orders_z = _z_score(orders_val, orders_mean, orders_std)
                revenue_z = _z_score(revenue_val, revenue_mean, revenue_std)
                orders_mz = _modified_z_score(orders_val, orders_median, orders_mad)
                revenue_mz = _modified_z_score(revenue_val, revenue_median, revenue_mad)

                if (
                    abs(orders_z) >= 2.5
                    or abs(revenue_z) >= 2.5
                    or abs(orders_mz) >= 3.5
                    or abs(revenue_mz) >= 3.5
                ):
                    anomalies.append(
                        {
                            "day": r.day.date().isoformat() if r.day else None,
                            "orders": orders_val,
                            "revenue": round(revenue_val, 2),
                            "orders_z": round(orders_z, 3),
                            "revenue_z": round(revenue_z, 3),
                            "orders_modified_z": round(orders_mz, 3),
                            "revenue_modified_z": round(revenue_mz, 3),
                        }
                    )

            return {
                "lookback_days": lookback_days,
                "series_days": len(rows),
                "metrics": {
                    "orders": {
                        "mean": round(orders_mean, 2),
                        "std_dev": round(orders_std, 2),
                        "median": round(float(orders_median), 2),
                        "mad": round(float(orders_mad), 2),
                    },
                    "revenue": {
                        "mean": round(revenue_mean, 2),
                        "std_dev": round(revenue_std, 2),
                        "median": round(float(revenue_median), 2),
                        "mad": round(float(revenue_mad), 2),
                    },
                },
                "thresholds": {
                    "z_score_abs": 2.5,
                    "modified_z_score_abs": 3.5,
                },
                "anomalies": anomalies,
            }
    except Exception as e:
        log.exception(f"Error in sales_analyze_anamoly: {e}")
        return {"error": str(e)}


@mcp.tool
async def sales_analyze_orders(lookback_days: int = 30) -> dict:
    """
    Return compact end-to-end analysis of orders.

    Args:
            lookback_days: Number of trailing days to include.

    Returns:
            Order KPIs with status, payment, and channel distributions.
    """
    try:
        end = now()
        start = end - timedelta(days=max(1, lookback_days))

        async with get_async_session() as session:
            summary_stmt = (
                select(
                    func.count(func.distinct(Order.id)).label("orders"),
                    func.coalesce(func.sum(OrderItem.quantity), 0).label("units"),
                    func.coalesce(
                        func.sum(OrderItem.quantity * OrderItem.unit_price),
                        0,
                    ).label("revenue"),
                    func.coalesce(func.avg(Order.discount_amount), 0).label("avg_discount"),
                )
                .select_from(Order)
                .outerjoin(OrderItem, OrderItem.order_id == Order.id)
                .where(and_(Order.ordered_at >= start, Order.ordered_at < end))
            )
            summary = (await session.execute(summary_stmt)).one()

            status_stmt = (
                select(Order.status, func.count(Order.id).label("count"))
                .where(and_(Order.ordered_at >= start, Order.ordered_at < end))
                .group_by(Order.status)
            )
            status_rows = (await session.execute(status_stmt)).all()

            payment_stmt = (
                select(Order.payment_status, func.count(Order.id).label("count"))
                .where(and_(Order.ordered_at >= start, Order.ordered_at < end))
                .group_by(Order.payment_status)
            )
            payment_rows = (await session.execute(payment_stmt)).all()

            channel_stmt = (
                select(
                    func.coalesce(Order.acquisition_channel, "unknown").label("channel"),
                    func.count(Order.id).label("count"),
                )
                .where(and_(Order.ordered_at >= start, Order.ordered_at < end))
                .group_by(Order.acquisition_channel)
                .order_by(func.count(Order.id).desc())
            )
            channel_rows = (await session.execute(channel_stmt)).all()

            orders = int(summary.orders or 0)
            revenue = _as_float(summary.revenue)
            return {
                "lookback_days": lookback_days,
                "orders": orders,
                "units": int(summary.units or 0),
                "revenue": round(revenue, 2),
                "aov": round((revenue / orders) if orders else 0.0, 2),
                "avg_discount_per_order": round(_as_float(summary.avg_discount), 2),
                "status_breakdown": [
                    {"status": _normalize_enum(r.status), "count": int(r.count)}
                    for r in status_rows
                ],
                "payment_breakdown": [
                    {
                        "payment_status": _normalize_enum(r.payment_status),
                        "count": int(r.count),
                    }
                    for r in payment_rows
                ],
                "channel_breakdown": [
                    {"channel": r.channel, "count": int(r.count)} for r in channel_rows
                ],
            }
    except Exception as e:
        log.exception(f"Error in sales_analyze_orders: {e}")
        return {"error": str(e)}


@mcp.tool
async def sales_analyze_performance_policy(lookback_days: int = 60) -> list[dict]:
    """
    Analyze policy performance based on policy_applied arrays.

    Args:
            lookback_days: Number of trailing days to include.

    Returns:
            Policy-level order, discount, and revenue metrics.
    """
    try:
        end = now()
        start = end - timedelta(days=max(1, lookback_days))

        async with get_async_session() as session:
            stmt = (
                select(
                    Order.id,
                    Order.policy_applied,
                    Order.discount_amount,
                    func.coalesce(
                        func.sum(OrderItem.quantity * OrderItem.unit_price),
                        0,
                    ).label("revenue"),
                )
                .select_from(Order)
                .outerjoin(OrderItem, OrderItem.order_id == Order.id)
                .where(and_(Order.ordered_at >= start, Order.ordered_at < end))
                .group_by(Order.id, Order.policy_applied, Order.discount_amount)
            )
            rows = (await session.execute(stmt)).all()

            metrics: dict[str, dict[str, float | int]] = {}
            for r in rows:
                policies = r.policy_applied or ["no_policy"]
                for policy in policies:
                    bucket = metrics.setdefault(
                        str(policy),
                        {
                            "orders": 0,
                            "discount_total": 0.0,
                            "revenue_total": 0.0,
                        },
                    )
                    bucket["orders"] = int(bucket["orders"]) + 1
                    bucket["discount_total"] = _as_float(bucket["discount_total"]) + _as_float(
                        r.discount_amount
                    )
                    bucket["revenue_total"] = _as_float(bucket["revenue_total"]) + _as_float(
                        r.revenue
                    )

            result = []
            for policy, data in metrics.items():
                orders = int(data["orders"])
                discount_total = _as_float(data["discount_total"])
                revenue_total = _as_float(data["revenue_total"])
                result.append(
                    {
                        "policy": policy,
                        "orders": orders,
                        "discount_total": round(discount_total, 2),
                        "revenue_total": round(revenue_total, 2),
                        "avg_discount_per_order": round(
                            (discount_total / orders) if orders else 0.0,
                            2,
                        ),
                    }
                )

            result.sort(key=lambda x: x["orders"], reverse=True)
            return result
    except Exception as e:
        log.exception(f"Error in sales_analyze_performance_policy: {e}")
        return [{"error": str(e)}]


@mcp.tool
async def sales_analyse_discountbasis(lookback_days: int = 60, limit: int = 20) -> list[dict]:
    """
    Analyze discount behavior against price, cost_price, and stock.

    Args:
            lookback_days: Number of trailing days to include.
            limit: Maximum products to return.

    Returns:
            Per-product selling-vs-list discount and margin context.
    """
    try:
        end = now()
        start = end - timedelta(days=max(1, lookback_days))

        async with get_async_session() as session:
            stmt = (
                select(
                    Product.id,
                    Product.sku,
                    Product.name,
                    Product.price,
                    Product.cost_price,
                    Product.stock_quantity,
                    func.coalesce(func.avg(OrderItem.unit_price), 0).label("avg_sold_price"),
                    func.coalesce(func.sum(OrderItem.quantity), 0).label("units"),
                )
                .select_from(Product)
                .outerjoin(OrderItem, OrderItem.product_id == Product.id)
                .outerjoin(Order, Order.id == OrderItem.order_id)
                .where(
                    Order.ordered_at.is_(None)
                    | and_(Order.ordered_at >= start, Order.ordered_at < end)
                )
                .group_by(
                    Product.id,
                    Product.sku,
                    Product.name,
                    Product.price,
                    Product.cost_price,
                    Product.stock_quantity,
                )
                .order_by(func.coalesce(func.sum(OrderItem.quantity), 0).desc())
                .limit(max(1, limit))
            )
            rows = (await session.execute(stmt)).all()

            output = []
            for r in rows:
                list_price = _as_float(r.price)
                cost_price = _as_float(r.cost_price)
                avg_sold = _as_float(r.avg_sold_price)
                units = int(r.units or 0)
                discount_value = max(0.0, list_price - avg_sold)
                discount_pct = (discount_value / list_price * 100.0) if list_price > 0 else 0.0
                margin_at_avg_sold = avg_sold - cost_price

                output.append(
                    {
                        "product_id": r.id,
                        "sku": r.sku,
                        "name": r.name,
                        "stock_quantity": int(r.stock_quantity or 0),
                        "units_sold": units,
                        "list_price": round(list_price, 2),
                        "avg_sold_price": round(avg_sold, 2),
                        "cost_price": round(cost_price, 2),
                        "discount_value": round(discount_value, 2),
                        "discount_pct": round(discount_pct, 2),
                        "margin_at_avg_sold": round(margin_at_avg_sold, 2),
                    }
                )

            return output
    except Exception as e:
        log.exception(f"Error in sales_analyse_discountbasis: {e}")
        return [{"error": str(e)}]
