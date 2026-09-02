import pytest
from uuid import uuid4
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_evaluate_transaction_valid_contract(async_client: AsyncClient):
    payload = {
        "user_id": str(uuid4()),
        "card_hash": "a1b2c3d4e5f67890abcdef1234567890abcdef12",
        "card_bin": "411111",
        "amount": 250.00,
        "currency": "USD",
        "ip_address": "198.51.100.42",
        "location": {
            "latitude": 40.7128,
            "longitude": -74.0060,
            "country": "US",
            "city": "New York"
        },
        "device_id": "dev_test_123",
        "timestamp": "2026-09-02T10:00:00Z"
    }
    response = await async_client.post("/api/v1/transactions/evaluate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "transaction_id" in data
    assert data["decision"] == "ALLOW"
    assert data["risk_score"] == 15
    assert "execution_time_ms" in data


@pytest.mark.asyncio
async def test_evaluate_transaction_high_risk_contract(async_client: AsyncClient):
    payload = {
        "user_id": str(uuid4()),
        "card_hash": "a1b2c3d4e5f67890abcdef1234567890abcdef12",
        "amount": 6500.00,
        "currency": "USD",
        "ip_address": "198.51.100.42",
        "location": {
            "latitude": 40.7128,
            "longitude": -74.0060,
            "country": "US"
        }
    }
    response = await async_client.post("/api/v1/transactions/evaluate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "BLOCK"
    assert data["risk_score"] == 85
    assert len(data["rules_triggered"]) > 0


@pytest.mark.asyncio
async def test_evaluate_transaction_validation_error(async_client: AsyncClient):
    # Invalid: negative amount and invalid IP address
    payload = {
        "user_id": str(uuid4()),
        "card_hash": "short",
        "amount": -50.00,
        "currency": "INVALID_CURRENCY",
        "ip_address": "not_an_ip",
        "location": {
            "latitude": 120.0,  # Invalid latitude (>90)
            "longitude": -74.0060,
            "country": "U"  # Min length 2
        }
    }
    response = await async_client.post("/api/v1/transactions/evaluate", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data


@pytest.mark.asyncio
async def test_rules_endpoints_contract(async_client: AsyncClient):
    # Test GET /rules
    get_res = await async_client.get("/api/v1/rules")
    assert get_res.status_code == 200
    rules = get_res.json()
    assert isinstance(rules, list)
    assert len(rules) >= 3

    # Test POST /rules with valid payload
    new_rule = {
        "rule_code": "CUSTOM_RISK_RULE",
        "name": "Custom Test Rule",
        "rule_type": "CUSTOM",
        "threshold_value": 10.0,
        "weight_points": 25,
        "is_active": True,
        "description": "Test custom rule description"
    }
    post_res = await async_client.post("/api/v1/rules", json=new_rule)
    assert post_res.status_code == 201
    created = post_res.json()
    assert created["rule_code"] == "CUSTOM_RISK_RULE"


@pytest.mark.asyncio
async def test_cases_endpoints_contract(async_client: AsyncClient):
    # Test GET /cases/pending
    get_res = await async_client.get("/api/v1/cases/pending")
    assert get_res.status_code == 200
    data = get_res.json()
    assert "items" in data
    assert "total" in data

    # Test POST /cases/{id}/resolve (Non-existent case)
    fake_case_id = str(uuid4())
    resolve_payload = {
        "action": "APPROVE",
        "resolution_notes": "Legitimate transaction confirmed via phone call."
    }
    res = await async_client.post(f"/api/v1/cases/{fake_case_id}/resolve", json=resolve_payload)
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_analytics_overview_contract(async_client: AsyncClient):
    response = await async_client.get("/api/v1/analytics/overview")
    assert response.status_code == 200
    data = response.json()
    assert "total_transactions_evaluated" in data
    assert "decisions_breakdown" in data
    assert "top_triggered_rules" in data
    assert "geographic_risk" in data
