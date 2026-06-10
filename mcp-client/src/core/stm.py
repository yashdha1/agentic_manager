"""Short-Term Memory (STM) backed by Redis.

Key schema
----------
stm:threads              → Redis SET   — all known thread IDs
stm:thread:{thread_id}   → Redis LIST  — JSON-encoded {role, content} dicts,
                                         newest items pushed to the right (RPUSH).

An optional TTL (seconds) is refreshed on every write.  When Redis is
unavailable the fallback ``InMemorySTM`` provides the same interface so the
rest of the application is unaffected.
"""

from __future__ import annotations

import json
import logging

logger = logging.getLogger(__name__)

_THREADS_KEY = "stm:threads"
_MSG_KEY_PREFIX = "stm:thread:"


class RedisSTM:
    """Async Redis-backed Short-Term Memory store for thread conversations."""

    def __init__(self, redis_url: str, ttl: int | None = None) -> None:
        import redis.asyncio as aioredis

        self._client: aioredis.Redis = aioredis.from_url(
            redis_url,
            socket_connect_timeout=5,
            decode_responses=True,
        )
        self._ttl = ttl  # seconds; None → no expiry

    # ── helpers ──────────────────────────────────────────────────────────────

    def _msg_key(self, thread_id: str) -> str:
        return f"{_MSG_KEY_PREFIX}{thread_id}"

    # ── public API ────────────────────────────────────────────────────────────

    async def create_thread(self, thread_id: str) -> None:
        """Register a thread in the thread-set (idempotent)."""
        await self._client.sadd(_THREADS_KEY, thread_id)

    async def thread_exists(self, thread_id: str) -> bool:
        return bool(await self._client.sismember(_THREADS_KEY, thread_id))

    async def list_threads(self) -> list[str]:
        members = await self._client.smembers(_THREADS_KEY)
        return sorted(members)

    async def append_message(self, thread_id: str, role: str, content: str) -> None:
        """Append a message to the thread's Redis list."""
        key = self._msg_key(thread_id)
        payload = json.dumps({"role": role, "content": content})
        pipe = self._client.pipeline()
        pipe.sadd(_THREADS_KEY, thread_id)
        pipe.rpush(key, payload)
        if self._ttl is not None:
            pipe.expire(key, self._ttl)
        await pipe.execute()
        logger.debug("STM append [%s] %s", thread_id, role)

    async def get_messages(self, thread_id: str) -> list[dict]:
        """Return all messages for a thread in insertion order."""
        raw: list[str] = await self._client.lrange(self._msg_key(thread_id), 0, -1)
        return [json.loads(r) for r in raw]

    async def close(self) -> None:
        await self._client.aclose()


class InMemorySTM:
    """Fallback STM when Redis is unavailable — same interface, in-process only."""

    def __init__(self) -> None:
        self._store: dict[str, list[dict]] = {}

    async def create_thread(self, thread_id: str) -> None:  # noqa: RUF006
        self._store.setdefault(thread_id, [])

    async def thread_exists(self, thread_id: str) -> bool:  # noqa: RUF006
        return thread_id in self._store

    async def list_threads(self) -> list[str]:  # noqa: RUF006
        return sorted(self._store.keys())

    async def append_message(self, thread_id: str, role: str, content: str) -> None:  # noqa: RUF006
        self._store.setdefault(thread_id, []).append({"role": role, "content": content})

    async def get_messages(self, thread_id: str) -> list[dict]:  # noqa: RUF006
        return list(self._store.get(thread_id, []))

    async def close(self) -> None:
        # No-op: in-memory store needs no teardown.
        pass
