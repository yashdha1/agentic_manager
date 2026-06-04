from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

from core.db.schemas import Order, OrderItem, Refund, Review
from sqlalchemy import select

_COMPLAINT_KEYWORDS: dict[str, list[str]] = {
	"quality": ["quality", "cheap", "broke", "broken", "defect", "defective"],
	"size_fit": ["size", "fit", "small", "large", "tight", "loose"],
	"shipping": ["shipping", "late", "delay", "delayed", "delivery"],
	"damaged": ["damaged", "scratch", "crack", "dent", "leak"],
	"not_as_described": ["not as described", "different", "misleading", "wrong item"],
	"performance": ["slow", "performance", "lag", "doesn't work", "stopped working"],
	"price_value": ["expensive", "overpriced", "not worth", "value"],
}

def _as_float(value: Any) -> float:
	if value is None:
		return 0.0
	if isinstance(value, Decimal):
		return float(value)
	return float(value)


def _parse_date(value: str) -> datetime:
	parsed = date.fromisoformat(value)
	return datetime.combine(parsed, datetime.min.time())


def _date_window(start_date: str, end_date: str) -> tuple[datetime, datetime]:
	start = _parse_date(start_date)
	end = _parse_date(end_date) + timedelta(days=1)
	if end <= start:
		raise ValueError("end_date must be on or after start_date")
	return start, end


def _normalize_enum(value: Any) -> str:
	return value.value if hasattr(value, "value") else str(value)


def _build_complaint_queries(product_id: int | None):
	review_stmt = select(Review.title, Review.body).where(Review.rating <= 2)
	refund_stmt = select(Refund.reason)

	if product_id is None:
		return review_stmt, refund_stmt

	review_stmt = review_stmt.where(Review.product_id == product_id)
	refund_stmt = (
		refund_stmt.select_from(Refund)
		.join(Order, Order.id == Refund.order_id)
		.join(OrderItem, OrderItem.order_id == Order.id)
		.where(OrderItem.product_id == product_id)
	)
	return review_stmt, refund_stmt


def _collect_complaint_evidence(review_rows: list, refund_rows: list) -> list[str]:
	evidence: list[str] = []
	for row in review_rows:
		text = " ".join([row.title or "", row.body or ""]).strip()
		if text:
			evidence.append(text)

	for row in refund_rows:
		if row.reason:
			evidence.append(row.reason)

	return evidence


def _rank_complaints(evidence: list[str], limit: int) -> list[dict]:
	counts = dict.fromkeys(_COMPLAINT_KEYWORDS.keys(), 0)
	samples: dict[str, list[str]] = {theme: [] for theme in _COMPLAINT_KEYWORDS}

	for text in evidence:
		lowered = text.lower()
		for theme, words in _COMPLAINT_KEYWORDS.items():
			if any(word in lowered for word in words):
				counts[theme] += 1
				if len(samples[theme]) < 3:
					samples[theme].append(text[:250])

	ranked = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)
	ranked = [item for item in ranked if item[1] > 0][: max(1, limit)]
	return [
		{"theme": theme, "count": count, "examples": samples[theme]}
		for theme, count in ranked
	]
