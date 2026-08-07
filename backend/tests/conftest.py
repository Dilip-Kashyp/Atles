"""
Pytest configuration and test fixtures for Atlas.
"""
import asyncio
from typing import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.config import get_settings
from app.infrastructure.database.base import Base
from app.main import app
from app.database.session import get_db

from sqlalchemy.pool import NullPool

TEST_DATABASE_URL = get_settings().database_url


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool, echo=False)
    async with engine.connect() as conn:
        trans = await conn.begin()
        async_session = async_sessionmaker(conn, expire_on_commit=False)
        async with async_session() as session:
            yield session
        await trans.rollback()
    await engine.dispose()


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()
