import os
import sys
import asyncio
from datetime import datetime, timedelta
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import AsyncClient
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

# Ensure tests can import the local `app` package by adding backend/ to sys.path
# This is required when running pytest from the backend folder or when Poetry
# is not installing the package into the environment.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Ensure required environment variables exist before importing application modules
os.environ.setdefault("GITHUB_CLIENT_ID", "test-client")
os.environ.setdefault("GITHUB_CLIENT_SECRET", "test-secret")
os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")
os.environ.setdefault("FRONTEND_URL", "http://localhost:3000")

from app.config import settings
from app.db import base
from app.db.base import Base, get_db
from app.main import app

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:?cache=shared"


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def db_engine():
    engine = create_async_engine(TEST_DATABASE_URL, future=True, connect_args={"uri": True})
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # Override application-wide engine and session factory
    base.engine = engine
    base.AsyncSessionLocal = SessionLocal

    async def override_get_db():
        async with SessionLocal() as session:
            try:
                yield session
            finally:
                await session.close()

    app.dependency_overrides[get_db] = override_get_db

    yield engine

    app.dependency_overrides.pop(get_db, None)
    await engine.dispose()


@pytest.fixture(scope="session")
def session_maker(db_engine):
    # db_engine fixture configures AsyncSessionLocal on base module
    return base.AsyncSessionLocal


@pytest_asyncio.fixture
async def client(db_engine):
    async with AsyncClient(app=app, base_url="http://testserver") as ac:
        yield ac


@pytest.fixture
def auth_cookies() -> dict:
    payload = {
        "sub": "user-1",
        "login": "tester",
        "access_token": "gho_test",
        "exp": datetime.utcnow() + timedelta(hours=settings.jwt_expiration_hours),
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return {"applens_token": token}
