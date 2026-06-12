import asyncio

from celery import Task

from src.core.logger import logger
from src.core.tracing import configure_langsmith_tracing
from src.pipelines.ingestion import run_pipeline
from src.workers import celery_app


@celery_app.task(
    name="ingest_document",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def ingest_document_task(self: Task, document_id: str, url: str) -> dict[str, str]:
    """Run the async ingestion pipeline inside a fresh event loop.

    Celery workers are synchronous; asyncio.run() gives each task its own loop
    so async SQLAlchemy / Qdrant / LangChain calls work without conflict.
    """
    configure_langsmith_tracing()
    logger.info(f"[task={self.request.id}] ingesting document {document_id}")
    try:
        result = asyncio.run(run_pipeline(document_id, url))
        return {"status": "ok", **result}
    except Exception as exc:
        logger.opt(exception=exc).error(
            "[task={}] failed for {}",
            self.request.id,
            document_id,
        )
        raise self.retry(exc=exc) from exc
