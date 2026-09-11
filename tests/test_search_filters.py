import pytest
from httpx import AsyncClient
from app.schemas.common import CaseStatusEnum

@pytest.mark.asyncio
async def test_search_transactions(auth_client: AsyncClient):
    response = await auth_client.get("/api/v1/transactions?search=test")
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_filter_transactions(auth_client: AsyncClient):
    response = await auth_client.get("/api/v1/transactions?transaction_type=PURCHASE&min_amount=10")
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_search_rules(auth_client: AsyncClient):
    response = await auth_client.get("/api/v1/rules?search=rule")
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_filter_rules(auth_client: AsyncClient):
    response = await auth_client.get("/api/v1/rules?is_active=true")
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_search_blocklist(auth_client: AsyncClient):
    response = await auth_client.get("/api/v1/blocklist?search=tempmail")
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_filter_blocklist(auth_client: AsyncClient):
    response = await auth_client.get("/api/v1/blocklist?entity_type=EMAIL_DOMAIN")
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_search_cases(auth_client: AsyncClient):
    response = await auth_client.get("/api/v1/cases?search=test")
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_filter_cases(auth_client: AsyncClient):
    response = await auth_client.get("/api/v1/cases?status=PENDING")
    assert response.status_code == 200
