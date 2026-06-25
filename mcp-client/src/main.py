from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.memory import MemorySaver


def _patch_redis_serializer() -> None:
    try:
        from langgraph.checkpoint.redis.jsonplus_redis import JsonPlusRedisSerializer
        from pydantic import BaseModel

        _orig_default = JsonPlusRedisSerializer._default_handler
        _orig_preprocess = JsonPlusRedisSerializer._preprocess_interrupts

        def _patched_default(self: Any, obj: Any) -> Any:  # type: ignore[override]
            if isinstance(obj, BaseModel):
                return obj.model_dump()
            return _orig_default(self, obj)

        def _patched_preprocess(self: Any, obj: Any) -> Any:  # type: ignore[override]
            from pydantic import BaseModel as _BM
            if isinstance(obj, _BM):
                return {k: self._preprocess_interrupts(v) for k, v in obj.model_dump().items()}
            return _orig_preprocess(self, obj)

        JsonPlusRedisSerializer._default_handler = _patched_default  # type: ignore[method-assign]
        JsonPlusRedisSerializer._preprocess_interrupts = _patched_preprocess  # type: ignore[method-assign]
    except ImportError:
        pass

_patch_redis_serializer()

import redis.asyncio as aioredis
from langgraph.checkpoint.redis.aio import AsyncRedisSaver

from src.api.v1 import router as api_router
from src.api.v1 import state as api_state
from src.core import ltm
from src.core.config import settings
from src.core.logger import logger
from src.core.pg import close_pool, ensure_pg_ready
from src.core.stm import InMemorySTM, RedisSTM
from src.core.tracing import configure_langsmith_tracing
from src.declarative.AgentSpec import _all_tools
from src.declarative.mcp_tools import prepare_workflow


async def _make_checkpointer(stack: AsyncExitStack):
    """Try Redis; fall back to in-memory if Redis is unavailable.""" 

    redis_url = f"redis://{settings.redis_host}:{settings.redis_port}"
    try:
        # Quick connectivity probe before handing to AsyncRedisSaver
        r = aioredis.from_url(redis_url, socket_connect_timeout=2)
        await r.ping()
        await r.aclose()
        checkpointer = await stack.enter_async_context(
            AsyncRedisSaver.from_conn_string(redis_url)
        )
        logger.info(f"Using Redis checkpointer at {redis_url}")
        return checkpointer, redis_url
    except Exception as exc:
        logger.warning(f"Redis unavailable ({exc}). Falling back to in-memory checkpointer.")
        return MemorySaver(), None


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]: 

    configure_langsmith_tracing()
    logger.info("Starting up — connecting to MCP server...")
    async with AsyncExitStack() as stack:
        checkpointer, redis_url = await _make_checkpointer(stack)

        if redis_url:
            api_state.stm = RedisSTM(redis_url, ttl=settings.redis_stm_ttl)
            logger.info("Using Redis STM (ttl={} s)", settings.redis_stm_ttl)
        else:
            api_state.stm = InMemorySTM()
            logger.warning("Using in-memory STM (data will be lost on restart).")
 
        try:
            await ensure_pg_ready()
        except Exception as exc:
            logger.warning("PostgreSQL unavailable ({}). Chat turns will not be persisted.", exc)
 
        _ltm_task = None
        if isinstance(api_state.stm, RedisSTM):
            try:
                await api_state.stm.enable_keyspace_notifications()
                _ltm_task = asyncio.create_task(
                    api_state.stm.subscribe_expiry_events(ltm.process_thread_expiry)
                )
            except Exception as exc:
                logger.warning("LTM subscriber could not start: {}", exc)

        await prepare_workflow(checkpointer)
        logger.info(f"MCP client is ready to serve requests. {len(_all_tools)} tools loaded.")
        yield

        if _ltm_task is not None:
            _ltm_task.cancel()

    await api_state.stm.close()
    await close_pool()
    logger.info("Shutting down the MCP client...")


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/")
async def root():
    return {"message": "Hello from the client"}