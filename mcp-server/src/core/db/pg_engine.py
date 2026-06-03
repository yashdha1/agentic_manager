from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core.config import settings
from core.db.schemas import Base

engine = create_async_engine(
    settings.PG_ASYNC_URL,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    echo=False,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    expire_on_commit=False,
)


@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async SQLAlchemy session, rolling back on error."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

async def ensure_schema_presence() -> None: 
    try: 
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("Tables ensured.")
    except Exception as e:
        print(f"Error ensuring tables: {e}")