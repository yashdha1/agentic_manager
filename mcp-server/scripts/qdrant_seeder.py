import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from core.db.qdrant_client import QdrantCollections, get_qdrant_client

DATASET = Path(__file__).parents[1] / "dataset"

_CATEGORY_TO_COLLECTION = {
    "policy": QdrantCollections.KB_POLICY,
    "marketing": QdrantCollections.KB_MARKETING,
    "campaign": QdrantCollections.KB_CAMPAIGN,
}


def seed_knowledgebase(client) -> None:
    with open(DATASET / "knowledgebase.csv", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            collection = _CATEGORY_TO_COLLECTION.get((row.get("Category") or "").strip().lower())
            if collection is None:
                continue
            client.upsert(
                collection=collection,
                text=row["Body"],
                payload={
                    "id": row["ID"],
                    "category": row.get("Category"),
                    "title": row["Title"],
                    "body": row["Body"],
                    "effective_date": row.get("effective_date"),
                    "status": row.get("status"),
                },
            )


if __name__ == "__main__":
    from core.db.qdrant_client import QdrantClientManager
    QdrantClientManager.create_collections()
    client = get_qdrant_client()
    seed_knowledgebase(client)
    print("Qdrant seeding complete.")
