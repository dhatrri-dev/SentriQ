from uuid import uuid4
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_client_role_cannot_modify_rules_regression(client_user: dict):
    """Regression: CLIENT role must be strictly forbidden (403) from creating, updating, or deleting risk rules."""
    client = client_user["client"]

    # Rule creation attempt
    create_res = await client.post(
        "/api/v1/rules",
        json={
            "rule_code": "FORBIDDEN_RULE",
            "rule_name": "Forbidden Rule",
            "rule_type": "CUSTOM",
            "threshold_value": 500.0,
            "risk_score_impact": 50,
            "description": "Unauthorized rule creation attempt"
        }
    )
    assert create_res.status_code == 403, f"Expected 403 Forbidden, got {create_res.status_code}"

    # Rule modification attempt
    patch_res = await client.patch(f"/api/v1/rules/{uuid4()}", json={"is_active": False})
    assert patch_res.status_code == 403

    # Rule deletion attempt
    del_res = await client.delete(f"/api/v1/rules/{uuid4()}")
    assert del_res.status_code == 403


@pytest.mark.asyncio
async def test_client_role_cannot_manage_blocklist_regression(client_user: dict):
    """Regression: CLIENT role must be forbidden (403) from adding, patching, or deleting blocklist entities."""
    client = client_user["client"]

    # Add blocklist attempt
    add_res = await client.post(
        "/api/v1/blocklist",
        json={"entity_type": "EMAIL_DOMAIN", "entity_value": "spam.org", "reason": "Unauthorized addition"}
    )
    assert add_res.status_code == 403

    # Patch blocklist attempt
    patch_res = await client.patch(f"/api/v1/blocklist/{uuid4()}", json={"is_active": False})
    assert patch_res.status_code == 403

    # Delete blocklist attempt
    del_res = await client.delete(f"/api/v1/blocklist/{uuid4()}")
    assert del_res.status_code == 403


@pytest.mark.asyncio
async def test_client_role_cannot_resolve_cases_regression(client_user: dict):
    """Regression: CLIENT role must be forbidden (403) from resolving investigation cases."""
    client = client_user["client"]

    resolve_res = await client.post(
        f"/api/v1/cases/{uuid4()}/resolve",
        json={"action": "APPROVE", "resolution_notes": "Unauthorized client resolution attempt"}
    )
    assert resolve_res.status_code == 403


@pytest.mark.asyncio
async def test_client_role_cannot_access_ip_intelligence_regression(client_user: dict):
    """Regression: CLIENT role must be forbidden (403) from accessing admin IP intelligence lookup."""
    client = client_user["client"]

    res = await client.get("/api/v1/ip-intel/lookup/198.51.100.1")
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_invalid_or_tampered_jwt_token_rejected(async_client: AsyncClient):
    """Regression: Invalid or tampered JWT tokens must be rejected with 401 Unauthorized."""
    tampered_headers = {"Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalidpayload.invalid_signature"}
    res = await async_client.get("/api/v1/auth/me", headers=tampered_headers)
    assert res.status_code == 401
    assert "x-request-id" in res.headers
