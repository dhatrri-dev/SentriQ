import pytest
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


