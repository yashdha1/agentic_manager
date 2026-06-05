import enum
import uuid
from functools import lru_cache

from langchain_openai import AzureOpenAIEmbeddings
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, ScoredPoint, VectorParams

from core.config import settings
from core.logger import logger


class QdrantCollections(enum.Enum):
    KB_POLICY = settings.KB_POLICY_COLLECTION
    KB_MARKETING = settings.KB_MARKETING_COLLECTION
    KB_CAMPAIGN = settings.KB_CAMPAIGN_COLLECTION
    THREAD = settings.THREAD_COLLECTION
    RESOLVER = settings.RESOLVER_COLLECTION


class QdrantClientManager:
    def __init__(self, url: str):
        self.url = url
        self.client: QdrantClient | None = None
        print()
        self._embeddings = AzureOpenAIEmbeddings(
            azure_deployment=settings.AZURE_EMBEDDING_MODEL,
            azure_endpoint=settings.AZURE_ENDPOINT,
            api_key=settings.AZURE_API_KEY,
            api_version=settings.AZURE_API_VERSION,
            dimensions=settings.AZURE_EMBEDDING_DIMENSIONS,
        )

    def get_client(self) -> QdrantClient:
        """
        QDRANT CLIENT
        """
        if self.client is None:
            self.client = QdrantClient(url=self.url)
        return self.client

    @classmethod
    def get_collections(cls) -> dict[str, str]:
        return {
            "policy": settings.KB_POLICY_COLLECTION,
            "marketing": settings.KB_MARKETING_COLLECTION,
            "campaign": settings.KB_CAMPAIGN_COLLECTION,
            "thread": settings.THREAD_COLLECTION,
            "resolver": settings.RESOLVER_COLLECTION,
        }

    @classmethod
    def create_collections(cls) -> None:
        """
        CREATE QDRANT COLLECTIONS IF THEY DON'T EXIST
        """
        try:
            client = get_qdrant_client().get_client()
            existing = {c.name for c in client.get_collections().collections}
            for col in QdrantCollections:
                if col.value not in existing:
                    client.create_collection(
                        collection_name=col.value,
                        vectors_config=VectorParams(
                            size=settings.AZURE_EMBEDDING_DIMENSIONS,
                            distance=Distance.COSINE,
                        ),
                    )
            logger.info("Qdrant collections created successfully.")
        except Exception as e:
            logger.error(f"Error creating collections: {e}")

    def upsert(self, collection: QdrantCollections, text: str, payload: dict) -> None:
        """
        UPSERTS THE QUERY USING AZURE OPENAI EMB
            ARGS -
                    collection: QdrantCollections - the collection to upsert in
                    text: str - the text to be embedded
                    payload: dict - the payload to be associated with the point
            RETURNS - None
        """
        vector = self.embed(text)
        self.get_client().upsert(
            collection_name=collection.value,
            points=[PointStruct(id=str(uuid.uuid4()), vector=vector, payload=payload)],
        )

    def search(
        self, collection: QdrantCollections, query: str, limit: int = 5
    ) -> list[ScoredPoint]:
        """
        SEARCHES THE QUERY USING AZURE OPENAI EMBEDDING MODEL
            ARGS -
                    collection: QdrantCollections - the collection to search in
                    query: str - the query to be searched
                    limit: int - the number of search results to return

            RETURNS - list[ScoredPoint] - the search results
        """
        vector = self.embed(query)
        # print(f"Searching collection '{collection.value}' with query vector: {vector[:5]}...")
        return (
            self.get_client()
            .query_points(
                collection_name=collection.value,
                query=vector,
                limit=limit,
            )
            .points
        )

    def embed(self, text: str) -> list[float]:
        """
        EMBED'S THE QUERY USING AZURE OPENAI EMBEDDING MODEL
            ARGS - text: str - the text to be embedded
            RETURNS - list[float] - the embedding vector
        """
        try:
            return self._embeddings.embed_query(text)
        except Exception as e:
            logger.exception(f"Embedding request failed: {e}")
            raise RuntimeError(
                f"Embedding provider is unreachable: {e}. "
                "Check AZURE endpoint/API key/API version and network access."
            ) from e


@lru_cache
def get_qdrant_client() -> QdrantClientManager:
    """
    POOLED QDRANT CLIENT
    """
    url = f"http://{settings.QDRANT_HOST}:{settings.QDRANT_PORT}"
    return QdrantClientManager(url=url)
