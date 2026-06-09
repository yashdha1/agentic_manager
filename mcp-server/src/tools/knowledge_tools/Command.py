from core.db.qdrant_client import QdrantCollections, get_qdrant_client
from core.logger import logger as log
from fastmcp import FastMCP
from qdrant_client.models import FieldCondition, Filter, MatchValue

mcp = FastMCP("ecomm_mcp_knowledge_commands")


def _find_point(collection: QdrantCollections, entry_id: str):
    """Locate a single Qdrant point by its payload ``id`` field."""
    client = get_qdrant_client().get_client()
    points, _ = client.scroll(
        collection_name=collection.value,
        scroll_filter=Filter(
            must=[FieldCondition(key="id", match=MatchValue(value=entry_id))]
        ),
        limit=1,
        with_payload=True,
    )
    return points[0] if points else None


def _apply_updates(point, **kwargs) -> dict:
    """Merge non-None keyword arguments into a copy of ``point.payload``."""
    updated = dict(point.payload)
    for key, value in kwargs.items():
        if value is not None:
            updated[key] = value
    return updated


@mcp.tool
def knowledge_update_marketing_strategy_hitl(
    entry_id: str,
    title: str | None = None,
    body: str | None = None,
    status: str | None = None,
) -> dict:
    """
    Update the metadata of a marketing strategy in the KB_MARKETING collection.

    Requires human approval before executing — the HITL middleware intercepts
    this call and raises a LangGraph interrupt. The update is only applied after
    the operator approves.

    At least one of ``title``, ``body``, or ``status`` must be provided.

    Args:
        entry_id: Logical ID of the marketing entry (payload ``id`` field).
        title:    New title text, or ``None`` to leave unchanged.
        body:     New body text, or ``None`` to leave unchanged.
        status:   New status value (e.g. ``"active"`` / ``"inactive"``), or ``None``.
    """
    if title is None and body is None and status is None:
        return {"error": "Provide at least one of: title, body, status."}

    try:
        point = _find_point(QdrantCollections.KB_MARKETING, entry_id)
        if point is None:
            return {"error": f"No marketing entry found with id='{entry_id}'."}

        updated_payload = _apply_updates(point, title=title, body=body, status=status)
        get_qdrant_client().get_client().set_payload(
            collection_name=QdrantCollections.KB_MARKETING.value,
            payload=updated_payload,
            points=[point.id],
        )
        log.info(f"knowledge_update_marketing_strategy: updated point {point.id} (id={entry_id})")
        return {"status": "updated", "entry_id": entry_id, "updated_fields": updated_payload}

    except Exception as e:
        log.exception(f"knowledge_update_marketing_strategy error: {e}")
        return {"error": "Failed to update marketing strategy.", "details": str(e)}


@mcp.tool
def knowledge_update_campaign_strategy_hitl(
    entry_id: str,
    title: str | None = None,
    body: str | None = None,
    status: str | None = None,
) -> dict:
    """
    Update the metadata of a campaign entry in the KB_CAMPAIGN collection.

    Requires human approval before executing — the HITL middleware intercepts
    this call and raises a LangGraph interrupt. The update is only applied after
    the operator approves.

    At least one of ``title``, ``body``, or ``status`` must be provided.

    Args:
        entry_id: Logical ID of the campaign entry (payload ``id`` field).
        title:    New title text, or ``None`` to leave unchanged.
        body:     New body text, or ``None`` to leave unchanged.
        status:   New status value (e.g. ``"active"`` / ``"inactive"``), or ``None``.
    """
    if title is None and body is None and status is None:
        return {"error": "Provide at least one of: title, body, status."}

    try:
        point = _find_point(QdrantCollections.KB_CAMPAIGN, entry_id)
        if point is None:
            return {"error": f"No campaign entry found with id='{entry_id}'."}

        updated_payload = _apply_updates(point, title=title, body=body, status=status)
        get_qdrant_client().get_client().set_payload(
            collection_name=QdrantCollections.KB_CAMPAIGN.value,
            payload=updated_payload,
            points=[point.id],
        )
        log.info(f"knowledge_update_campaign_strategy: updated point {point.id} (id={entry_id})")
        return {"status": "updated", "entry_id": entry_id, "updated_fields": updated_payload}

    except Exception as e:
        log.exception(f"knowledge_update_campaign_strategy error: {e}")
        return {"error": "Failed to update campaign strategy.", "details": str(e)}


@mcp.tool
def knowledge_update_policy_status_hitl(
    entry_id: str,
    status: str,
) -> dict:
    """
    Update the ``status`` field of a policy in the KB_POLICY collection.

    Requires human approval before executing — the HITL middleware intercepts
    this call and raises a LangGraph interrupt. The status change is only applied
    after the operator approves.

    Args:
        entry_id: Logical ID of the policy entry (payload ``id`` field).
        status:   New status value (e.g. ``"active"`` or ``"inactive"``).
    """
    try:
        point = _find_point(QdrantCollections.KB_POLICY, entry_id)
        if point is None:
            return {"error": f"No policy entry found with id='{entry_id}'."}

        current_status = point.payload.get("status")
        get_qdrant_client().get_client().set_payload(
            collection_name=QdrantCollections.KB_POLICY.value,
            payload={"status": status},
            points=[point.id],
        )
        log.info(
            f"knowledge_update_policy_status: updated point {point.id} "
            f"(id={entry_id}) status {current_status!r} -> {status!r}"
        )
        return {
            "status": "updated",
            "entry_id": entry_id,
            "previous_status": current_status,
            "new_status": status,
        }

    except Exception as e:
        log.exception(f"knowledge_update_policy_status error: {e}")
        return {"error": "Failed to update policy status.", "details": str(e)}

