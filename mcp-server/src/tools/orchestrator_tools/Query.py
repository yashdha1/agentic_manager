from core.db.qdrant_client import QdrantCollections, get_qdrant_client
from fastmcp import FastMCP

mcp = FastMCP("ecomm_mcp_orchestrator_queries")


@mcp.tool
def orchestrator_get_related_policies(query: str, limit: int = 5) -> list[dict]:
    """
    Search only kb_policy_collection for policies related to the user query.
    """
    try:
        results = get_qdrant_client().search(
            collection=QdrantCollections.KB_POLICY,
            query=query,
            limit=max(1, limit),
        )
        return [
            {
                "score": float(point.score),
                "id": point.payload.get("id"),
                "title": point.payload.get("title"),
                "body": point.payload.get("body"),
                "category": point.payload.get("category"),
                "effective_date": point.payload.get("effective_date"),
                "status": point.payload.get("status"),
            }
            for point in results
        ]
    except Exception as e:
        return [
            {
                "error": "Failed to retrieve related policies from kb_policy_collection.",
                "details": str(e),
            }
        ]
