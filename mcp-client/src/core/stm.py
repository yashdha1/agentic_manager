from __future__ import annotations

import json

from .config import settings
from .logger import logger


class RedisSTM:
    """Async Redis-backed Short-Term Memory store for thread conversations."""

    def __init__(self, redis_url: str, ttl: int | None = None) -> None:
        import redis.asyncio as aioredis  # rare

        self._client: aioredis.Redis = aioredis.from_url(
            redis_url,
            socket_connect_timeout=5,
            decode_responses=True,
        )
        self._ttl = ttl  

  
    def _msg_key(self, thread_id: str) -> str:
        return f"{settings.stm_msg_key_prefix}{thread_id}"
 
    async def create_thread(self, thread_id: str) -> None:
        """Register a thread in the thread-set (idempotent)."""
        await self._client.sadd(settings.stm_thread_key, thread_id)

    async def thread_exists(self, thread_id: str) -> bool:
        return bool(await self._client.sismember(settings.stm_thread_key, thread_id))

    async def list_threads(self) -> list[str]:
        members = await self._client.smembers(settings.stm_thread_key)
        return sorted(members)

    async def append_message(self, thread_id: str, role: str, content: str) -> None:
        """Append a message to the thread's Redis list."""
        key = self._msg_key(thread_id)

        payload = json.dumps({"role": role, "content": content})

        # pipe batch jobs:-
        pipe = self._client.pipeline()
        pipe.sadd(settings.stm_thread_key, thread_id)
        pipe.rpush(key, payload)
        if self._ttl is not None:
            pipe.expire(key, self._ttl)
        await pipe.execute()

        logger.info("STM append [{}] {}", thread_id, role)

    async def get_messages(self, thread_id: str) -> list[dict]:
        """Return all messages for a thread in insertion order."""
        raw: list[str] = await self._client.lrange(self._msg_key(thread_id), 0, -1)
        return [json.loads(r) for r in raw]

    async def close(self) -> None:
        await self._client.aclose()

    # LTM expiry hooks 
    async def enable_keyspace_notifications(self) -> None:
        """Enable Redis keyspace notifications for expired events (required for LTM)."""
        await self._client.config_set("notify-keyspace-events", "Kx")
        logger.info("Redis keyspace notifications enabled (expired events).")

    async def subscribe_expiry_events(self, callback) -> None:
        """
            Listen for STM key expiry events and invoke *callback(thread_id)* for each.
        """
        channel = "__keyevent@0__:expired"
        pubsub = self._client.pubsub()
        await pubsub.subscribe(channel)
        logger.info("Subscribed to Redis expiry channel for LTM processing.")
        
        async for message in pubsub.listen():
            if message["type"] == "message":
                key: str = message["data"]
                if key.startswith(settings.stm_msg_key_prefix):
                    thread_id = key[len(settings.stm_msg_key_prefix):]
                    try:
                        await callback(thread_id)
                    except Exception as exc:
                        logger.error("LTM callback failed for thread {}: {}", thread_id, exc)


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
