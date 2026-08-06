from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import get_settings

settings = get_settings()

# Async Engine and SessionMaker (used by API requests)
async_engine = create_async_engine(settings.database_url, echo=False)
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Sync Engine and SessionMaker (used for setup/migrations or scripts)
sync_engine = create_engine(settings.database_sync_url, echo=False)
SessionLocal = sessionmaker(
    bind=sync_engine,
    expire_on_commit=False,
)


async def get_db():
    """FastAPI dependency for accessing the async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
