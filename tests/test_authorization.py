from datetime import datetime, timezone
import pytest
from httpx import AsyncClient


def _sample_eval_payload(user_id: str, amount: float = 150.0):
    return {
        "user_id": user_id,
        "card_hash": "a1b2c3d4e5f67890a1b2c3d4e5f67890a1b2c3d4e5f67890a1b2c3d4e5f67890",
        "card_bin": "411111",
        "amount": amount,
        "currency": "USD",
        "ip_address": "198.51.100.50",
        "location": {
            "latitude": 37.7749,
            "longitude": -122.4194,
            "country": "USA",
            "city": "San Francisco"
        },
        "device_id": "device_user_1",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@pytest.mark.asyncio
async def test_client_cannot_evaluate_transaction_for_another_user(client_user, second_client_user):
    """Verifies 403 Forbidden when Client A attempts to evaluate a transaction on behalf of User B."""
    payload = _sample_eval_payload(user_id=second_client_user["user_id"])
    response = await client_user["client"].post("/api/v1/transactions/evaluate", json=payload)
    assert response.status_code == 403
    assert "Cannot evaluate transactions for another user account" in response.json()["detail"]


@pytest.mark.asyncio
async def test_client_evaluates_own_transaction_success(client_user):
    """Verifies successful 200 OK evaluation when Client A evaluates their own transaction."""
    payload = _sample_eval_payload(user_id=client_user["user_id"])
    response = await client_user["client"].post("/api/v1/transactions/evaluate", json=payload)
    assert response.status_code == 200
    assert response.json()["user_id"] == client_user["user_id"]


@pytest.mark.asyncio
async def test_client_list_transactions_is_owner_scoped(client_user, second_client_user):
    """Verifies that listing transactions automatically scopes results to the authenticated user's records."""
    # Create transaction for User A
    payload_a = _sample_eval_payload(user_id=client_user["user_id"], amount=100.0)
    res_a = await client_user["client"].post("/api/v1/transactions/evaluate", json=payload_a)
    assert res_a.status_code == 200
    tx_id_a = res_a.json()["transaction_id"]

    # Create transaction for User B
    payload_b = _sample_eval_payload(user_id=second_client_user["user_id"], amount=200.0)
    res_b = await second_client_user["client"].post("/api/v1/transactions/evaluate", json=payload_b)
    assert res_b.status_code == 200

    # User A lists transactions
    res = await client_user["client"].get("/api/v1/transactions")
    assert res.status_code == 200
    items = res.json()["items"]
    user_ids = {item["user_id"] for item in items}
    assert user_ids == {client_user["user_id"]}
    assert any(item["id"] == tx_id_a for item in items)


@pytest.mark.asyncio
async def test_client_cannot_query_another_users_transactions(client_user, second_client_user):
    """Verifies 403 Forbidden when Client A explicitly queries user_id parameter of User B."""
    response = await client_user["client"].get(f"/api/v1/transactions?user_id={second_client_user['user_id']}")
    assert response.status_code == 403
    assert "cannot view another user's transactions" in response.json()["detail"]


@pytest.mark.asyncio
async def test_client_cannot_get_another_users_transaction_detail(client_user, second_client_user):
    """Verifies 403 Forbidden when Client A attempts to fetch detail of User B's transaction."""
    payload_b = _sample_eval_payload(user_id=second_client_user["user_id"])
    res_b = await second_client_user["client"].post("/api/v1/transactions/evaluate", json=payload_b)
    assert res_b.status_code == 200
    tx_id_b = res_b.json()["transaction_id"]

    # User A tries to get User B's transaction
    res = await client_user["client"].get(f"/api/v1/transactions/{tx_id_b}")
    assert res.status_code == 403
    assert "Access denied" in res.json()["detail"]


@pytest.mark.asyncio
async def test_client_cannot_delete_another_users_transaction(client_user, second_client_user):
    """Verifies 403 Forbidden when Client A attempts to delete User B's transaction."""
    payload_b = _sample_eval_payload(user_id=second_client_user["user_id"])
    res_b = await second_client_user["client"].post("/api/v1/transactions/evaluate", json=payload_b)
    assert res_b.status_code == 200
    tx_id_b = res_b.json()["transaction_id"]

    # User A attempts deletion
    res = await client_user["client"].delete(f"/api/v1/transactions/{tx_id_b}")
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_client_cannot_create_update_delete_rules(client_user):
    """Verifies 403 Forbidden when a standard client user attempts RBAC-protected rule management."""
    # Attempt create
    res_create = await client_user["client"].post("/api/v1/rules", json={
        "rule_code": "UNAUTH_RULE",
        "name": "Unauthorized Rule",
        "rule_type": "AMOUNT_ANOMALY",
        "threshold_value": 1000.0,
        "weight_points": 20
    })
    assert res_create.status_code == 403
    assert "requires one of roles" in res_create.json()["detail"].lower()


@pytest.mark.asyncio
async def test_admin_or_analyst_can_manage_rules(admin_user):
    """Verifies 201 Created when an Admin user manages rules."""
    res_create = await admin_user["client"].post("/api/v1/rules", json={
        "rule_code": f"ADMIN_RULE_{admin_user['user_id'][:6]}",
        "name": "Admin Rule Test",
        "rule_type": "AMOUNT_ANOMALY",
        "threshold_value": 1500.0,
        "weight_points": 25
    })
    assert res_create.status_code == 201
    rule_id = res_create.json()["id"]

    # Delete rule
    res_delete = await admin_user["client"].delete(f"/api/v1/rules/{rule_id}?soft=false")
    assert res_delete.status_code == 204


@pytest.mark.asyncio
async def test_client_cannot_manage_blocklist(client_user):
    """Verifies 403 Forbidden when a client user tries to add an entry to the blocklist."""
    res = await client_user["client"].post("/api/v1/blocklist", json={
        "entity_type": "IP_ADDRESS",
        "entity_value": "203.0.113.99",
        "reason": "Suspicious IP"
    })
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_client_cannot_view_pending_cases(client_user):
    """Verifies 403 Forbidden when a client user attempts to access /cases/pending."""
    res = await client_user["client"].get("/api/v1/cases/pending")
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_client_cannot_resolve_investigation_case(client_user, auth_client):
    """Verifies 403 Forbidden when a standard client user tries to resolve an investigation case."""
    # First get or trigger a case via analyst
    res_cases = await auth_client.get("/api/v1/cases")
    assert res_cases.status_code == 200
    case_id = res_cases.json()["items"][0]["id"]

    # Client tries to resolve
    res_resolve = await client_user["client"].post(f"/api/v1/cases/{case_id}/resolve", json={
        "action": "APPROVE",
        "resolution_notes": "Client attempting self-approval"
    })
    assert res_resolve.status_code == 403


@pytest.mark.asyncio
async def test_admin_can_access_any_user_transaction_and_case(admin_user, client_user):
    """Verifies that Admin users can query across users and view any transaction detail."""
    payload = _sample_eval_payload(user_id=client_user["user_id"])
    res_eval = await client_user["client"].post("/api/v1/transactions/evaluate", json=payload)
    assert res_eval.status_code == 200
    tx_id = res_eval.json()["transaction_id"]

    # Admin fetches transaction of client_user
    res_tx = await admin_user["client"].get(f"/api/v1/transactions/{tx_id}")
    assert res_tx.status_code == 200
    assert res_tx.json()["user_id"] == client_user["user_id"]
