import pytest
from uuid import uuid4
from httpx import AsyncClient, ASGITransport
from app.main import app as fastapi_app
from app.core.database import get_db, engine, Base
from tests.db_fixtures import TestSessionLocal, setup_test_database  # noqa: F401
import app.models  # noqa: F401


async def override_get_db():
    async with TestSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


fastapi_app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
async def ensure_db_tables():
    """Ensure database tables exist for all async tests."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


@pytest.fixture
async def async_client():
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
async def auth_token(async_client: AsyncClient) -> str:
    """Registers a fresh test user and returns its JWT bearer token."""
    email = f"testuser_{uuid4().hex[:8]}@sentriq.io"
    res = await async_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "testpass123", "role": "ANALYST"}
    )
    assert res.status_code == 201, f"Auth setup failed: {res.text}"
    return res.json()["access_token"]


@pytest.fixture
async def auth_client(async_client: AsyncClient, auth_token: str) -> AsyncClient:
    """Returns an AsyncClient pre-configured with a valid Bearer auth header."""
    async_client.headers.update({"Authorization": f"Bearer {auth_token}"})
    return async_client
