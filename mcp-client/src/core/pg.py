"""Async PostgreSQL connection pool (asyncpg) for mcp-client.

Connects to the same Postgres instance used by mcp-server.
"""

from __future__ import annotations

import asyncpg

from src.core.config import settings
from src.core.logger import logger

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            host=settings.postgres_host,
            port=settings.postgres_port,
            user=settings.postgres_user,
            password=settings.postgres_password,
            database=settings.postgres_db,
            min_size=1,
            max_size=5,
        )
    return _pool


async def ensure_pg_ready() -> None:
    """Verify connectivity at startup."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.fetchval("SELECT 1")
    logger.info("PostgreSQL connection pool ready.")


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
