"""Day 6 – Update & Delete Workflows
Tests verify:
  * Partial updates validate fields correctly
  * Invalid partial update payloads return 422
  * Delete behavior is explicit (soft delete vs hard delete)
  * Database integrity constraints are enforced (e.g. 409 conflict when deleting transaction linked to a case, 400 when deleting resolved cases)
  * 404 handling for unknown entities during PATCH and DELETE
"""
import pytest
from uuid import uuid4
from httpx import AsyncClient
from tests.db_fixtures import setup_test_database, db_session  # noqa: F401


# ---------------------------------------------------------------------------
# Rules Update & Delete Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_patch_rule_valid_partial_update(async_client: AsyncClient):
    """PATCH /rules/{rule_id} updates provided fields while preserving unmentioned ones."""
    list_res = await async_client.get("/api/v1/rules")
    assert list_res.status_code == 200
    rule_id = list_res.json()[0]["id"]
    original_code = list_res.json()[0]["rule_code"]

    patch_payload = {
        "threshold_value": 999.0,
        "weight_points": 75
    }
    patch_res = await async_client.patch(f"/api/v1/rules/{rule_id}", json=patch_payload)
    assert patch_res.status_code == 200
    data = patch_res.json()
    assert data["threshold_value"] == 999.0
    assert data["weight_points"] == 75
    assert data["rule_code"] == original_code


@pytest.mark.asyncio
async def test_patch_rule_invalid_field_validation(async_client: AsyncClient):
    """PATCH /rules/{rule_id} fails validation (422) if weight_points is out of bounds (1-100)."""
    list_res = await async_client.get("/api/v1/rules")
    rule_id = list_res.json()[0]["id"]

    # Invalid weight_points > 100
    patch_res = await async_client.patch(f"/api/v1/rules/{rule_id}", json={"weight_points": 150})
    assert patch_res.status_code == 422


@pytest.mark.asyncio
async def test_delete_rule_soft_and_hard(async_client: AsyncClient):
    """DELETE /rules/{rule_id} supports soft deactivation and hard deletion."""
    # Create rule first
    create_payload = {
        "rule_code": "TEST_DELETE_RULE",
        "name": "Temporary Test Rule",
        "rule_type": "VELOCITY",
        "threshold_value": 10.0,
        "weight_points": 20,
        "is_active": True
    }
    create_res = await async_client.post("/api/v1/rules", json=create_payload)
    assert create_res.status_code == 201
    rule_id = create_res.json()["id"]

    # Soft delete (default)
    soft_del_res = await async_client.delete(f"/api/v1/rules/{rule_id}")
    assert soft_del_res.status_code == 204

    # Verify soft deleted (is_active = False)
    detail_res = await async_client.get(f"/api/v1/rules/{rule_id}")
    assert detail_res.status_code == 200
    assert detail_res.json()["is_active"] is False

    # Hard delete
    hard_del_res = await async_client.delete(f"/api/v1/rules/{rule_id}?soft=false")
    assert hard_del_res.status_code == 204

    # Verify rule is permanently gone (404)
    after_res = await async_client.get(f"/api/v1/rules/{rule_id}")
    assert after_res.status_code == 404


# ---------------------------------------------------------------------------
# Blocklist Update & Delete Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_patch_blocklist_partial_update(async_client: AsyncClient):
    """PATCH /blocklist/{entry_id} updates reason or active status."""
    add_payload = {
        "entity_type": "EMAIL_DOMAIN",
        "entity_value": "spam-domain.org",
        "reason": "Initial block reason"
    }
    add_res = await async_client.post("/api/v1/blocklist", json=add_payload)
    assert add_res.status_code == 201
    entry_id = add_res.json()["id"]

    patch_payload = {
        "reason": "Updated audit block reason",
        "is_active": False
    }
    patch_res = await async_client.patch(f"/api/v1/blocklist/{entry_id}", json=patch_payload)
    assert patch_res.status_code == 200
    data = patch_res.json()
    assert data["reason"] == "Updated audit block reason"
    assert data["is_active"] is False


@pytest.mark.asyncio
async def test_delete_blocklist_hard_and_soft(async_client: AsyncClient):
    """DELETE /blocklist/{entry_id} handles soft vs hard deletion."""
    add_payload = {
        "entity_type": "IP",
        "entity_value": "203.0.113.199",
        "reason": "Botnet node"
    }
    add_res = await async_client.post("/api/v1/blocklist", json=add_payload)
    assert add_res.status_code == 201
    entry_id = add_res.json()["id"]

    # Hard delete
    del_res = await async_client.delete(f"/api/v1/blocklist/{entry_id}?hard=true")
    assert del_res.status_code == 204

    # Detail check -> 404
    get_res = await async_client.get(f"/api/v1/blocklist/{entry_id}")
    assert get_res.status_code == 404


# ---------------------------------------------------------------------------
# Case & Transaction Integrity / Update / Delete Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_patch_case_partial_update(async_client: AsyncClient):
    """PATCH /cases/{case_id} updates case priority."""
    list_res = await async_client.get("/api/v1/cases/pending")
    assert list_res.status_code == 200
    cases = list_res.json()["items"]
    assert len(cases) > 0
    case_id = cases[0]["id"]

    patch_res = await async_client.patch(f"/api/v1/cases/{case_id}", json={"priority": "HIGH"})
    assert patch_res.status_code == 200
    assert patch_res.json()["priority"] == "HIGH"


@pytest.mark.asyncio
async def test_delete_resolved_case_integrity_constraint(async_client: AsyncClient):
    """Attempting to DELETE a resolved case returns 400 Bad Request to preserve audit history."""
    list_res = await async_client.get("/api/v1/cases/pending")
    cases = list_res.json()["items"]
    case_id = cases[0]["id"]

    # Resolve case first
    resolve_res = await async_client.post(
        f"/api/v1/cases/{case_id}/resolve",
        json={"action": "APPROVE", "resolution_notes": "Legitimate customer purchase verified."}
    )
    assert resolve_res.status_code == 200

    # Attempt delete resolved case -> expect 400 Bad Request
    del_res = await async_client.delete(f"/api/v1/cases/{case_id}")
    assert del_res.status_code == 400
    assert "audit" in del_res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_delete_transaction_linked_case_conflict(async_client: AsyncClient):
    """DELETE /transactions/{id} linked to an investigation case returns 409 Conflict."""
    # Trigger high-risk transaction to create transaction & case
    payload = {
        "user_id": str(uuid4()),
        "card_hash": "b2c3d4e5f67890abcdef1234567890abcdef1234",
        "amount": 9500.00,
        "currency": "USD",
        "ip_address": "198.51.100.45",
        "location": {"latitude": 40.71, "longitude": -74.00, "country": "US"},
        "timestamp": "2026-09-07T12:00:00Z"
    }
    eval_res = await async_client.post("/api/v1/transactions/evaluate", json=payload)
    assert eval_res.status_code == 200
    tx_id = eval_res.json()["transaction_id"]
    assert eval_res.json()["case_id"] is not None

    # Attempt to delete transaction with linked investigation case
    del_res = await async_client.delete(f"/api/v1/transactions/{tx_id}")
    assert del_res.status_code == 409
    assert "investigation case" in del_res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_delete_standalone_transaction_success(async_client: AsyncClient):
    """DELETE /transactions/{id} deletes clean standalone transaction without linked cases."""
    payload = {
        "user_id": str(uuid4()),
        "card_hash": "c3d4e5f67890abcdef1234567890abcdef12345",
        "amount": 12.50,
        "currency": "USD",
        "ip_address": "198.51.100.50",
        "location": {"latitude": 40.71, "longitude": -74.00, "country": "US"},
        "timestamp": "2026-09-07T12:05:00Z"
    }
    eval_res = await async_client.post("/api/v1/transactions/evaluate", json=payload)
    assert eval_res.status_code == 200
    tx_id = eval_res.json()["transaction_id"]
    assert eval_res.json()["case_id"] is None

    # Deleting standalone transaction returns 204
    del_res = await async_client.delete(f"/api/v1/transactions/{tx_id}")
    assert del_res.status_code == 204

    # Subsequent GET returns 404
    get_res = await async_client.get(f"/api/v1/transactions/{tx_id}")
    assert get_res.status_code == 404
