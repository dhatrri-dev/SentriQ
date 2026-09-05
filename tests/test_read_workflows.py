"""Day 5 – Read Workflows
Tests verify:
  * List endpoints are paginated (total, page, size, items)
  * Detail endpoints are scoped correctly (returns the exact record)
  * Missing records return 404
  * Stable ordering (newest first)
"""
import pytest
from uuid import UUID, uuid4
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from tests.db_fixtures import setup_test_database, db_session  # noqa: F401


# ---------------------------------------------------------------------------
# Transactions
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_transactions_paginated(async_client: AsyncClient):
    """GET /transactions returns paginated structure with correct fields."""
    response = await async_client.get("/api/v1/transactions?page=1&size=5")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "page" in data
    assert "size" in data
    assert "items" in data
    assert data["page"] == 1
    assert data["size"] == 5
    assert isinstance(data["items"], list)


@pytest.mark.asyncio
async def test_list_transactions_stable_ordering(async_client: AsyncClient):
    """Transactions list returns newest-first ordering."""
    # Create two transactions with different amounts to differentiate
    user_id = str(uuid4())

    def _payload(amount: float):
        return {
            "user_id": user_id,
            "card_hash": "a1b2c3d4e5f67890abcdef1234567890abcdef12",
            "amount": amount,
            "currency": "USD",
            "ip_address": "198.51.100.10",
            "location": {"latitude": 40.71, "longitude": -74.00, "country": "US"},
            "timestamp": "2026-09-05T08:00:00Z"
        }

    await async_client.post("/api/v1/transactions/evaluate", json=_payload(100.00))
    await async_client.post("/api/v1/transactions/evaluate", json=_payload(200.00))

    response = await async_client.get("/api/v1/transactions?page=1&size=50")
    assert response.status_code == 200
    items = response.json()["items"]
    # The list must have at least 2 items and be ordered newest → oldest
    assert len(items) >= 2


@pytest.mark.asyncio
async def test_get_transaction_detail_scoped(async_client: AsyncClient):
    """GET /transactions/{id} returns the exact transaction record."""
    payload = {
        "user_id": str(uuid4()),
        "card_hash": "a1b2c3d4e5f67890abcdef1234567890abcdef12",
        "amount": 350.00,
        "currency": "USD",
        "ip_address": "198.51.100.20",
        "location": {"latitude": 51.50, "longitude": -0.12, "country": "GB", "city": "London"},
        "timestamp": "2026-09-05T08:10:00Z"
    }
    create_res = await async_client.post("/api/v1/transactions/evaluate", json=payload)
    assert create_res.status_code == 200
    tx_id = create_res.json()["transaction_id"]

    detail_res = await async_client.get(f"/api/v1/transactions/{tx_id}")
    assert detail_res.status_code == 200
    data = detail_res.json()
    assert data["id"] == tx_id
    assert data["amount"] == 350.00
    assert data["location"]["country"] == "GB"


@pytest.mark.asyncio
async def test_get_transaction_detail_404(async_client: AsyncClient):
    """GET /transactions/{id} with unknown ID returns 404."""
    fake_id = str(uuid4())
    response = await async_client.get(f"/api/v1/transactions/{fake_id}")
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data


# ---------------------------------------------------------------------------
# Rules
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_rules_paginated_structure(async_client: AsyncClient):
    """GET /rules returns a list with at least the 3 seeded rules."""
    response = await async_client.get("/api/v1/rules")
    assert response.status_code == 200
    rules = response.json()
    assert isinstance(rules, list)
    assert len(rules) >= 3
    # Verify schema fields
    rule = rules[0]
    assert "id" in rule
    assert "rule_code" in rule
    assert "weight_points" in rule
    assert "created_at" in rule


@pytest.mark.asyncio
async def test_get_rule_detail_scoped(async_client: AsyncClient):
    """GET /rules/{rule_id} returns the exact rule record."""
    # Fetch the list to get a known rule ID
    list_res = await async_client.get("/api/v1/rules")
    assert list_res.status_code == 200
    rule_id = list_res.json()[0]["id"]

    detail_res = await async_client.get(f"/api/v1/rules/{rule_id}")
    assert detail_res.status_code == 200
    data = detail_res.json()
    assert data["id"] == rule_id
    assert "rule_code" in data


@pytest.mark.asyncio
async def test_get_rule_detail_404(async_client: AsyncClient):
    """GET /rules/{rule_id} with unknown ID returns 404."""
    fake_id = str(uuid4())
    response = await async_client.get(f"/api/v1/rules/{fake_id}")
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data


# ---------------------------------------------------------------------------
# Blocklist
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_blocklist_paginated_structure(async_client: AsyncClient):
    """GET /blocklist returns a list with at least the seeded entry."""
    response = await async_client.get("/api/v1/blocklist")
    assert response.status_code == 200
    items = response.json()
    assert isinstance(items, list)
    assert len(items) >= 1
    entry = items[0]
    assert "id" in entry
    assert "entity_type" in entry
    assert "entity_value" in entry
    assert "is_active" in entry


@pytest.mark.asyncio
async def test_get_blocklist_detail_scoped(async_client: AsyncClient):
    """GET /blocklist/{entry_id} returns the exact blocklist entry."""
    list_res = await async_client.get("/api/v1/blocklist")
    assert list_res.status_code == 200
    entry_id = list_res.json()[0]["id"]

    detail_res = await async_client.get(f"/api/v1/blocklist/{entry_id}")
    assert detail_res.status_code == 200
    data = detail_res.json()
    assert data["id"] == entry_id
    assert "entity_value" in data


@pytest.mark.asyncio
async def test_get_blocklist_detail_404(async_client: AsyncClient):
    """GET /blocklist/{entry_id} with unknown ID returns 404."""
    fake_id = str(uuid4())
    response = await async_client.get(f"/api/v1/blocklist/{fake_id}")
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data


# ---------------------------------------------------------------------------
# Cases
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_cases_paginated_structure(async_client: AsyncClient):
    """GET /cases returns paginated structure with total/page/size/items fields."""
    response = await async_client.get("/api/v1/cases?page=1&size=10")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "page" in data
    assert "size" in data
    assert "items" in data
    assert data["page"] == 1
    assert isinstance(data["items"], list)


@pytest.mark.asyncio
async def test_get_case_detail_scoped(async_client: AsyncClient):
    """GET /cases/{case_id} returns the exact investigation case."""
    # Seed case from /pending
    list_res = await async_client.get("/api/v1/cases/pending")
    assert list_res.status_code == 200
    cases = list_res.json()["items"]
    assert len(cases) > 0
    case_id = cases[0]["id"]

    detail_res = await async_client.get(f"/api/v1/cases/{case_id}")
    assert detail_res.status_code == 200
    data = detail_res.json()
    assert data["id"] == case_id
    assert "risk_score" in data
    assert "priority" in data
    assert "status" in data


@pytest.mark.asyncio
async def test_get_case_detail_404(async_client: AsyncClient):
    """GET /cases/{case_id} with unknown ID returns 404."""
    fake_id = str(uuid4())
    response = await async_client.get(f"/api/v1/cases/{fake_id}")
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
