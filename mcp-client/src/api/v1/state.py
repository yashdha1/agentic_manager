"""Shared STM (Short-Term Memory) handle for thread message history.

``stm`` is initialised at application startup (see ``main.py``) and is
either a :class:`~src.core.stm.RedisSTM` (when Redis is reachable) or an
:class:`~src.core.stm.InMemorySTM` fallback.  All read/write operations are
async so callers must ``await`` them.
"""

from __future__ import annotations

from src.core.stm import InMemorySTM, RedisSTM

# Populated during the FastAPI lifespan by main.py.
stm: RedisSTM | InMemorySTM = InMemorySTM()
