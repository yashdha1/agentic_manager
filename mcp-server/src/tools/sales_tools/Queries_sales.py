from typing import Literal

from core.db.pg_engine import get_async_session
from core.db.schemas import Order, OrderItem, Product, Refund, Review
from core.logger import logger as log
from fastmcp import FastMCP
from sqlalchemy import and_, func, select

from .helpers import (
	_as_float,
	_build_complaint_queries,
	_collect_complaint_evidence,
	_date_window,
	_normalize_enum,
	_rank_complaints,
)

mcp = FastMCP("ecomm_mcp_sales_queries")

@mcp.tool
async def sales_get_products_by_category(category: str, limit: int = 25) -> list[dict]:
	"""
	Return products in a category.

	Args:
		category: Category name (case-insensitive partial match).
		limit: Maximum number of products to return.

	Returns:
		List of matching products ordered by name.
	"""
	try:
		async with get_async_session() as session:
			stmt = (
				select(Product)
				.where(func.lower(Product.category).like(f"%{category.lower()}%"))
				.order_by(Product.name.asc())
				.limit(max(1, limit))
			)
			result = await session.execute(stmt)
			rows = result.scalars().all()
			log.info(f"Retrieved {len(rows)} products for category '{category}'")
			return [
				{
					"id": p.id,
					"sku": p.sku,
					"name": p.name,
					"category": p.category,
					"sub_category": p.sub_category,
					"brand": p.brand,
					"price": _as_float(p.price),
					"stock_quantity": p.stock_quantity,
					"is_active": p.is_active,
				}
				for p in rows
			]
	except Exception as e:
		log.exception(f"Error in get_products_by_category: {e}")
		return [{"error": str(e)}]

@mcp.tool
async def sales_get_products_by_subcategory(sub_category: str, limit: int = 25) -> list[dict]:
	"""
	Return products in a sub-category.

	Args:
		sub_category: Sub-category name (case-insensitive partial match).
		limit: Maximum number of products to return.

	Returns:
		List of matching products ordered by name.
	"""
	try:
		async with get_async_session() as session:
			stmt = (
				select(Product)
				.where(func.lower(Product.sub_category).like(f"%{sub_category.lower()}%"))
				.order_by(Product.name.asc())
				.limit(max(1, limit))
			)
			result = await session.execute(stmt)
			rows = result.scalars().all()
			log.info(f"Retrieved {len(rows)} products for sub_category '{sub_category}'")
			return [
				{
					"id": p.id,
					"sku": p.sku,
					"name": p.name,
					"category": p.category,
					"sub_category": p.sub_category,
					"brand": p.brand,
					"price": _as_float(p.price),
					"stock_quantity": p.stock_quantity,
					"is_active": p.is_active,
				}
				for p in rows
			]
	except Exception as e:
		log.exception(f"Error in get_products_by_subcategory: {e}")
		return [{"error": str(e)}]

@mcp.tool
async def sales_get_products_by_brand(brand: str, limit: int = 25) -> list[dict]:
	"""
	Return products for a brand.

	Args:
		brand: Brand name (case-insensitive partial match).
		limit: Maximum number of products to return.

	Returns:
		List of matching products ordered by name.
	"""
	try:
		async with get_async_session() as session:
			stmt = (
				select(Product)
				.where(func.lower(Product.brand).like(f"%{brand.lower()}%"))
				.order_by(Product.name.asc())
				.limit(max(1, limit))
			)
			result = await session.execute(stmt)
			rows = result.scalars().all()
			log.info(f"Retrieved {len(rows)} products for brand '{brand}'")
			return [
				{
					"id": p.id,
					"sku": p.sku,
					"name": p.name,
					"category": p.category,
					"sub_category": p.sub_category,
					"brand": p.brand,
					"price": _as_float(p.price),
					"stock_quantity": p.stock_quantity,
					"is_active": p.is_active,
				}
				for p in rows
			]
	except Exception as e:
		log.exception(f"Error in get_products_by_brand: {e}")
		return [{"error": str(e)}]

@mcp.tool
async def sales_get_product_by_sku(sku: str) -> dict:
	"""
	Return a single product by SKU.

	Args:
		sku: Exact SKU value.

	Returns:
		Full product record, or an error if not found.
	"""
	try:
		async with get_async_session() as session:
			stmt = select(Product).where(func.lower(Product.sku) == sku.lower())
			result = await session.execute(stmt)
			row = result.scalars().first()
			if not row:
				return {"error": f"Product with SKU '{sku}' not found"}

			log.info(f"Retrieved product by sku '{sku}': product_id={row.id}")
			return {
				"id": row.id,
				"sku": row.sku,
				"name": row.name,
				"description": row.description,
				"category": row.category,
				"sub_category": row.sub_category,
				"brand": row.brand,
				"price": _as_float(row.price),
				"cost_price": _as_float(row.cost_price),
				"stock_quantity": row.stock_quantity,
				"is_active": row.is_active,
				"created_at": row.created_at.isoformat() if row.created_at else None,
				"updated_at": row.updated_at.isoformat() if row.updated_at else None,
			}
	except Exception as e:
		log.exception(f"Error in get_product_by_sku: {e}")
		return {"error": str(e)}

@mcp.tool
async def sales_get_per_product_sales(
	start_date: str,
	end_date: str,
	sort_by: Literal["revenue", "units", "orders"] = "revenue",
	sort_order: Literal["asc", "desc"] = "desc",
	limit: int = 20,
) -> list[dict]:
	"""
	Return per-product sales rankings for a date range.

	Args:
		start_date: Inclusive start date in ISO format (YYYY-MM-DD).
		end_date: Inclusive end date in ISO format (YYYY-MM-DD).
		sort_by: Ranking metric (revenue, units, or orders).
		sort_order: Sorting direction (asc or desc).
		limit: Maximum number of products to return.

	Returns:
		Product-level revenue, units, and order count.
	"""
	try:
		start, end = _date_window(start_date, end_date)
		async with get_async_session() as session:
			revenue_expr = func.sum(OrderItem.quantity * OrderItem.unit_price).label("revenue")
			units_expr = func.sum(OrderItem.quantity).label("units")
			orders_expr = func.count(func.distinct(Order.id)).label("orders")

			metric_map = {
				"revenue": revenue_expr,
				"units": units_expr,
				"orders": orders_expr,
			}
			metric = metric_map.get(sort_by, revenue_expr)

			stmt = (
				select(
					Product.id,
					Product.sku,
					Product.name,
					Product.category,
					revenue_expr,
					units_expr,
					orders_expr,
				)
				.select_from(OrderItem)
				.join(Order, Order.id == OrderItem.order_id)
				.join(Product, Product.id == OrderItem.product_id)
				.where(and_(Order.ordered_at >= start, Order.ordered_at < end))
				.group_by(Product.id, Product.sku, Product.name, Product.category)
				.limit(max(1, limit))
			)

			stmt = stmt.order_by(metric.asc() if sort_order == "asc" else metric.desc())
			rows = (await session.execute(stmt)).all()

			output = [
				{
					"rank": idx,
					"product_id": r.id,
					"sku": r.sku,
					"name": r.name,
					"category": r.category,
					"revenue": round(_as_float(r.revenue), 2),
					"units": int(r.units or 0),
					"orders": int(r.orders or 0),
				}
				for idx, r in enumerate(rows, start=1)
			]
			log.info(
				f"Retrieved {len(output)} product sales rows for "
				f"{start_date}..{end_date}, sort={sort_by}"
			)
			return output
	except Exception as e:
		log.exception(f"Error in sales_get_per_product_sales: {e}")
		return [{"error": str(e)}]

@mcp.tool
async def sales_get_product_sales_region(
	start_date: str,
	end_date: str,
	limit: int = 25,
) -> list[dict]:
	"""
	Return sales by shipping region for a date range.

	Args:
		start_date: Inclusive start date in ISO format (YYYY-MM-DD).
		end_date: Inclusive end date in ISO format (YYYY-MM-DD).
		limit: Maximum number of regions to return.

	Returns:
		Region-level revenue, orders, and units grouped by country and city.
	"""
	try:
		start, end = _date_window(start_date, end_date)
		async with get_async_session() as session:
			stmt = (
				select(
					func.coalesce(Order.shipping_country, "Unknown").label("country"),
					func.coalesce(Order.shipping_city, "Unknown").label("city"),
					func.count(func.distinct(Order.id)).label("orders"),
					func.sum(OrderItem.quantity).label("units"),
					func.sum(OrderItem.quantity * OrderItem.unit_price).label("revenue"),
				)
				.select_from(Order)
				.join(OrderItem, OrderItem.order_id == Order.id)
				.where(and_(Order.ordered_at >= start, Order.ordered_at < end))
				.group_by(Order.shipping_country, Order.shipping_city)
				.order_by(func.sum(OrderItem.quantity * OrderItem.unit_price).desc())
				.limit(max(1, limit))
			)
			rows = (await session.execute(stmt)).all()
			log.info(f"Retrieved region sales rows for {start_date}..{end_date}: {len(rows)}")
			return [
				{
					"country": r.country,
					"city": r.city,
					"orders": int(r.orders or 0),
					"units": int(r.units or 0),
					"revenue": round(_as_float(r.revenue), 2),
				}
				for r in rows
			]
	except Exception as e:
		log.exception(f"Error in sales_get_product_sales_region: {e}")
		return [{"error": str(e)}]

@mcp.tool
async def sales_get_products_reviews(product_id: int, limit: int = 50) -> list[dict]:
	"""
	Return product reviews.

	Args:
		product_id: product ID.
		limit: Maximum review rows to return.

	Returns:
		Review rows with product and customer metadata.
	"""
	try:
		async with get_async_session() as session:
			stmt = (
				select(
					Review.id,
					Review.product_id,
					Product.name.label("product_name"),
					Review.user_id,
					Review.rating,
					Review.title,
					Review.body,
					Review.verified_purchase,
					Review.helpful_votes,
					Review.flagged,
					Review.reviewed_at,
				)
				.join(Product, Product.id == Review.product_id)
				.order_by(Review.reviewed_at.desc())
				.limit(max(1, limit))
			)
			if product_id is not None:
				stmt = stmt.where(Review.product_id == product_id)

			rows = (await session.execute(stmt)).all()
			log.info(
				f"Retrieved {len(rows)} reviews"
				f"{' for product_id=' + str(product_id) if product_id else ''}"
			)
			return [
				{
					"id": r.id,
					"product_id": r.product_id,
					"product_name": r.product_name,
					"user_id": r.user_id,
					"rating": int(r.rating),
					"title": r.title,
					"body": r.body,
					"verified_purchase": r.verified_purchase,
					"helpful_votes": r.helpful_votes,
					"flagged": r.flagged,
					"reviewed_at": r.reviewed_at.isoformat() if r.reviewed_at else None,
				}
				for r in rows
			]
	except Exception as e:
		log.exception(f"Error in sales_get_products_reviews: {e}")
		return [{"error": str(e)}]

@mcp.tool
async def sales_get_products_refunds(product_id: int | None = None, limit: int = 50) -> list[dict]:
	"""
	Return refund records with products context.

	Args:
		product_id: product ID filter.
		limit: Maximum refund rows to return.

	Returns:
		Refund rows with order and product-level context.
	"""
	try:
		async with get_async_session() as session:
			stmt = (
				select(
					Refund.id,
					Refund.order_id,
					Refund.refund_amount,
					Refund.reason,
					Refund.status,
					Refund.processed_at,
					func.array_agg(func.distinct(Product.id)).label("product_ids"),
					func.array_agg(func.distinct(Product.name)).label("product_names"),
				)
				.select_from(Refund)
				.join(Order, Order.id == Refund.order_id)
				.join(OrderItem, OrderItem.order_id == Order.id)
				.join(Product, Product.id == OrderItem.product_id)
			)
			if product_id is not None:
				stmt = stmt.where(OrderItem.product_id == product_id)
			stmt = (
				stmt
				.group_by(
					Refund.id,
					Refund.order_id,
					Refund.refund_amount,
					Refund.reason,
					Refund.status,
					Refund.processed_at,
				)
				.order_by(Refund.id.desc())
				.limit(max(1, limit))
			)

			rows = (await session.execute(stmt)).all()
			log.info(
				f"Retrieved {len(rows)} refunds"
				f"{' for product_id=' + str(product_id) if product_id else ''}"
			)
			return [
				{
					"refund_id": r.id,
					"order_id": r.order_id,
					"refund_amount": round(_as_float(r.refund_amount), 2),
					"reason": r.reason,
					"status": _normalize_enum(r.status),
					"processed_at": r.processed_at.isoformat() if r.processed_at else None,
					"product_ids": r.product_ids or [],
					"product_names": r.product_names or [],
				}
				for r in rows
			]
	except Exception as e:
		log.exception(f"Error in sales_get_products_refunds: {e}")
		return [{"error": str(e)}]

@mcp.tool
async def sales_get_common_complaints(product_id: int | None = None, limit: int = 10) -> dict:
	"""
	Return common complaint themes from low-rating reviews and refund reasons.

	Args:
		product_id: Optional product ID filter.
		limit: Maximum number of complaint themes to return.

	Returns:
		Ranked complaint themes with counts and sample evidence.
	"""
	try:
		async with get_async_session() as session:
			review_stmt, refund_stmt = _build_complaint_queries(product_id)

			review_rows = (await session.execute(review_stmt)).all()
			refund_rows = (await session.execute(refund_stmt)).all()
			evidence = _collect_complaint_evidence(review_rows, refund_rows)
			themes = _rank_complaints(evidence, limit)

			payload = {
				"product_id": product_id,
				"source_records": len(evidence),
				"themes": themes,
			}
			log.info(
				"Computed complaint themes"
				+ (f" for product_id={product_id}" if product_id is not None else "")
			)
			return payload
	except Exception as e:
		log.exception(f"Error in sales_get_common_complaints: {e}")
		return {"error": str(e)}
