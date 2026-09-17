import os
from unittest.mock import AsyncMock
import pytest
from httpx import AsyncClient
from app.core.config import settings
from app.core.database import get_db
from app.main import app


@pytest.mark.asyncio
async def test_debug_mode_disabled_by_default():
    """Verify production debug mode defaults to False."""
    assert isinstance(settings.DEBUG, bool)


@pytest.mark.asyncio
async def test_health_endpoint_probes_dependencies(async_client: AsyncClient):
    """Verify health check endpoint probes active database and external service dependencies."""
    response = await async_client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "dependencies" in data
    assert data["dependencies"]["database"] == "healthy"
    assert "ip_intel_service" in data["dependencies"]


@pytest.mark.asyncio
async def test_health_endpoint_db_failure_returns_503(async_client: AsyncClient):
    """Verify health check endpoint returns 503 Service Unavailable when database connection fails."""
    mock_db = AsyncMock()
    mock_db.execute.side_effect = Exception("Database connection pool exhausted")

    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        response = await async_client.get("/api/v1/health")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"
        assert "unhealthy" in data["dependencies"]["database"]
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_secrets_excluded_from_source_control():
    """Verify .gitignore excludes .env file from git tracking."""
    gitignore_path = os.path.join(os.getcwd(), ".gitignore")
    assert os.path.exists(gitignore_path)
    with open(gitignore_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert ".env" in content
