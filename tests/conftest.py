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
    """Registers a fresh analyst test user and returns its JWT bearer token."""
    email = f"testuser_{uuid4().hex[:8]}@sentriq.io"
    res = await async_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "testpass123", "role": "ANALYST"}
    )
    assert res.status_code == 201, f"Auth setup failed: {res.text}"
    return res.json()["access_token"]


@pytest.fixture
async def auth_client(async_client: AsyncClient, auth_token: str) -> AsyncClient:
    """Returns an AsyncClient pre-configured with a valid Bearer auth header for an ANALYST."""
    async_client.headers.update({"Authorization": f"Bearer {auth_token}"})
    return async_client


async def _create_test_user_client(base_client: AsyncClient, role: str = "CLIENT"):
    email = f"{role.lower()}_{uuid4().hex[:8]}@sentriq.io"
    password = "password123"
    res = await base_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "role": role}
    )
    assert res.status_code == 201, f"Failed creating test user ({role}): {res.text}"
    data = res.json()
    user_id = data["user"]["id"]
    token = data["access_token"]

    transport = ASGITransport(app=fastapi_app)
    client = AsyncClient(transport=transport, base_url="http://test", headers={"Authorization": f"Bearer {token}"})
    return user_id, token, client


@pytest.fixture
async def client_user(async_client: AsyncClient):
    """Fixture providing a standard CLIENT user details (user_id, token, client)."""
    user_id, token, client = await _create_test_user_client(async_client, role="CLIENT")
    yield {"user_id": user_id, "token": token, "client": client}
    await client.aclose()


@pytest.fixture
async def second_client_user(async_client: AsyncClient):
    """Fixture providing a second distinct CLIENT user details (user_id, token, client)."""
    user_id, token, client = await _create_test_user_client(async_client, role="CLIENT")
    yield {"user_id": user_id, "token": token, "client": client}
    await client.aclose()


@pytest.fixture
async def admin_user(async_client: AsyncClient):
    """Fixture providing an ADMIN user details (user_id, token, client)."""
    user_id, token, client = await _create_test_user_client(async_client, role="ADMIN")
    yield {"user_id": user_id, "token": token, "client": client}
    await client.aclose()

