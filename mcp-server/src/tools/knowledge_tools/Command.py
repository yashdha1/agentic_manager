from core.db.qdrant_client import QdrantCollections, get_qdrant_client
from core.logger import logger as log
from fastmcp import FastMCP
from qdrant_client.models import FieldCondition, Filter, MatchValue

mcp = FastMCP("ecomm_mcp_knowledge_commands")
HITL_CONFIRM_INSTRUCTION = "Review the preview and call again with confirmed=True to apply."


def _find_point(collection: QdrantCollections, entry_id: str):
    """
    Locate a single Qdrant point by its payload ``id`` field.

    Args:
        collection: The Qdrant collection to search.
        entry_id:   The logical record ID stored in the ``id`` payload field
                    (e.g. ``"MK-006"``, ``"CA-007"``, ``"PA-011"``).

    Returns:
        The matching ``PointStruct`` or ``None`` when not found.
    """
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
    """
    Merge non-None keyword arguments into a copy of ``point.payload``.

    Args:
        point:   A Qdrant ``PointStruct`` whose ``payload`` will be used as base.
        **kwargs: Fields to overwrite (skipped when value is ``None``).

    Returns:
        New payload dict with updates applied.
    """
    updated = dict(point.payload)
    for key, value in kwargs.items():
        if value is not None:
            updated[key] = value
    return updated


@mcp.tool
def knowledge_update_marketing_strategy(
    entry_id: str,
    title: str | None = None,
    body: str | None = None,
    status: str | None = None,
    confirmed: bool = False,
) -> dict:
    """
    HITL tool to update the metadata of a marketing strategy in the KB_MARKETING collection.

    Locates the entry by its logical ``entry_id`` (e.g. ``"MK-006"``) and
    overwrites only the fields you supply. At least one of ``title``, ``body``,
    or ``status`` must be provided.

    Step 1 — ``confirmed=False`` (default): validates that the entry exists and
        returns a preview showing current values alongside proposed changes.
        No write occurs.
    Step 2 — ``confirmed=True``: calls ``set_payload`` on the matched point to
        persist the updates.

    Args:
        entry_id: Logical ID of the marketing entry (payload ``id`` field).
        title:    New title text, or ``None`` to leave unchanged.
        body:     New body text, or ``None`` to leave unchanged.
        status:   New status value (e.g. ``"active"`` / ``"inactive"``), or ``None``.
        confirmed: Set to ``True`` to commit after reviewing the preview.

    Returns:
        Preview dict on Step 1, confirmation dict on Step 2, or
        ``{"error": ...}`` on failure.
    """
    if title is None and body is None and status is None:
        return {"error": "Provide at least one of: title, body, status."}

    try:
        point = _find_point(QdrantCollections.KB_MARKETING, entry_id)
        if point is None:
            return {"error": f"No marketing entry found with id='{entry_id}'."}

        updated_payload = _apply_updates(point, title=title, body=body, status=status)

        if not confirmed:
            return {
                "preview": True,
                "entry_id": entry_id,
                "current": {
                    "title": point.payload.get("title"),
                    "body": point.payload.get("body"),
                    "status": point.payload.get("status"),
                },
                "proposed": {k: updated_payload[k] for k in ("title", "body", "status")},
                "instructions": HITL_CONFIRM_INSTRUCTION,
            }

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
def knowledge_update_campaign_strategy(
    entry_id: str,
    title: str | None = None,
    body: str | None = None,
    status: str | None = None,
    confirmed: bool = False,
) -> dict:
    """
    HITL tool to update the metadata of a campaign entry in the KB_CAMPAIGN collection.

    Locates the entry by its logical ``entry_id`` (e.g. ``"CA-006"``) and
    overwrites only the fields you supply. At least one of ``title``, ``body``,
    or ``status`` must be provided.

    Step 1 — ``confirmed=False`` (default): validates that the entry exists and
        returns a preview showing current values alongside proposed changes.
        No write occurs.
    Step 2 — ``confirmed=True``: calls ``set_payload`` on the matched point to
        persist the updates.

    Args:
        entry_id: Logical ID of the campaign entry (payload ``id`` field).
        title:    New title text, or ``None`` to leave unchanged.
        body:     New body text, or ``None`` to leave unchanged.
        status:   New status value (e.g. ``"active"`` / ``"inactive"``), or ``None``.
        confirmed: Set to ``True`` to commit after reviewing the preview.

    Returns:
        Preview dict on Step 1, confirmation dict on Step 2, or
        ``{"error": ...}`` on failure.
    """
    if title is None and body is None and status is None:
        return {"error": "Provide at least one of: title, body, status."}

    try:
        point = _find_point(QdrantCollections.KB_CAMPAIGN, entry_id)
        if point is None:
            return {"error": f"No campaign entry found with id='{entry_id}'."}

        updated_payload = _apply_updates(point, title=title, body=body, status=status)

        if not confirmed:
            return {
                "preview": True,
                "entry_id": entry_id,
                "current": {
                    "title": point.payload.get("title"),
                    "body": point.payload.get("body"),
                    "status": point.payload.get("status"),
                },
                "proposed": {k: updated_payload[k] for k in ("title", "body", "status")},
                "instructions": HITL_CONFIRM_INSTRUCTION,
            }

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
def knowledge_update_policy_status(
    entry_id: str,
    status: str,
    confirmed: bool = False,
) -> dict:
    """
    HITL tool to update the ``status`` field of a policy in the KB_POLICY collection.

    Locates the entry by its logical ``entry_id`` (e.g. ``"PA-011"``) and
    flips its ``status`` to the supplied value.

    Step 1 — ``confirmed=False`` (default): validates that the entry exists and
        returns a preview showing the current status and the proposed new status.
        No write occurs.
    Step 2 — ``confirmed=True``: calls ``set_payload`` on the matched point to
        persist the new status.

    Args:
        entry_id: Logical ID of the policy entry (payload ``id`` field).
        status:   New status value (e.g. ``"active"`` or ``"inactive"``).
        confirmed: Set to ``True`` to commit after reviewing the preview.

    Returns:
        Preview dict on Step 1, confirmation dict on Step 2, or
        ``{"error": ...}`` on failure.
    """
    try:
        point = _find_point(QdrantCollections.KB_POLICY, entry_id)
        if point is None:
            return {"error": f"No policy entry found with id='{entry_id}'."}

        current_status = point.payload.get("status")

        if not confirmed:
            return {
                "preview": True,
                "entry_id": entry_id,
                "title": point.payload.get("title"),
                "current_status": current_status,
                "proposed_status": status,
                "instructions": HITL_CONFIRM_INSTRUCTION,
            }

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
