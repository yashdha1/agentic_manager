from core.db.qdrant_client import QdrantCollections, get_qdrant_client
from core.logger import logger as log
from fastmcp import FastMCP

mcp = FastMCP("ecomm_mcp_knowledge_queries")


def _point_to_dict(point) -> dict:
    return {
        "score": round(float(point.score), 4),
        "id": point.payload.get("id"),
        "title": point.payload.get("title"),
        "body": point.payload.get("body"),
        "effective_date": point.payload.get("effective_date"),
        "status": point.payload.get("status"),
    }


@mcp.tool
def knowledge_get_campaign_information(query: str, limit: int = 5) -> list[dict]:
    """
    Semantic search over the campaign knowledge base (KB_CAMPAIGN collection).

    Embeds ``query`` and returns the top ``limit`` matching campaign entries
    ordered by relevance score (highest first).

    Args:
        query: Natural-language description of the campaign topic to search for.
        limit: Maximum number of results to return. Defaults to 5.

    Returns:
        List of dicts with ``score``, ``id``, ``title``, ``body``,
        ``effective_date``, and ``status``.
        Returns ``[{"error": ..., "details": ...}]`` on failure.
    """
    try:
        results = get_qdrant_client().search(
            collection=QdrantCollections.KB_CAMPAIGN,
            query=query,
            limit=max(1, limit),
        )
        log.info(f"knowledge_get_campaign_information: {len(results)} hits for '{query}'")
        return [_point_to_dict(p) for p in results]
    except Exception as e:
        log.exception(f"knowledge_get_campaign_information error: {e}")
        return [{"error": "Failed to retrieve campaign information.", "details": str(e)}]


@mcp.tool
def knowledge_get_marketing_strategies(query: str, limit: int = 5) -> list[dict]:
    """
    Semantic search over the marketing strategy knowledge base (KB_MARKETING collection).

    Embeds ``query`` and returns the top ``limit`` matching marketing strategy
    entries ordered by relevance score (highest first).

    Args:
        query: Natural-language description of the marketing topic to search for.
        limit: Maximum number of results to return. Defaults to 5.

    Returns:
        List of dicts with ``score``, ``id``, ``title``, ``body``,
        ``effective_date``, and ``status``.
        Returns ``[{"error": ..., "details": ...}]`` on failure.
    """
    try:
        results = get_qdrant_client().search(
            collection=QdrantCollections.KB_MARKETING,
            query=query,
            limit=max(1, limit),
        )
        log.info(f"knowledge_get_marketing_strategies: {len(results)} hits for '{query}'")
        return [_point_to_dict(p) for p in results]
    except Exception as e:
        log.exception(f"knowledge_get_marketing_strategies error: {e}")
        return [{"error": "Failed to retrieve marketing strategies.", "details": str(e)}]


@mcp.tool
def knowledge_search_resolver_memory(query: str, limit: int = 5) -> list[dict]:
    """
    Semantic search over past HITL (Human-in-the-Loop) resolutions stored in the
    resolver_memory collection.

    Use this to find how similar issues were handled in the past — e.g. what
    action was approved or rejected for a product update, refund, or order change.

    Args:
        query: Natural-language description of the issue or action to look up.
        limit: Maximum number of results to return. Defaults to 5.

    Returns:
        List of dicts with ``score``, ``tool_name``, ``original_args``,
        ``decisions``, ``thread_id``, and ``timestamp``.
        Returns ``[{"error": ..., "details": ...}]`` on failure.
    """
    try:
        results = get_qdrant_client().search(
            collection=QdrantCollections.RESOLVER,
            query=query,
            limit=max(1, limit),
        )
        log.info(f"knowledge_search_resolver_memory: {len(results)} hits for '{query}'")
        return [
            {
                "score": round(float(p.score), 4),
                "tool_name": p.payload.get("tool_name"),
                "original_args": p.payload.get("original_args"),
                "decisions": p.payload.get("decisions"),
                "thread_id": p.payload.get("thread_id"),
                "timestamp": p.payload.get("timestamp"),
            }
            for p in results
        ]
    except Exception as e:
        log.exception(f"knowledge_search_resolver_memory error: {e}")
        return [{"error": "Failed to search resolver memory.", "details": str(e)}]
