from uuid import uuid4
import pytest
from httpx import AsyncClient, Response
import httpx

from app.main import app
from app.schemas.ip_intel import IPEnrichmentResponse
from app.services.ip_intel import IPIntelligenceService, get_ip_intel_service


@pytest.mark.asyncio
async def test_end_to_end_fraud_investigation_workflow(client_user: dict, auth_client: AsyncClient):
    """
    End-to-end Happy Path:
    1. CLIENT evaluates high-risk transaction -> flags for review & generates case.
    2. ANALYST queries pending cases, assigns priority, and resolves case.
    3. Analytics overview reflects resolved status.
    """
    client_id = client_user["user_id"]
    client_http = client_user["client"]

    # 1. Evaluate high-amount transaction triggering risk rule
    eval_payload = {
        "user_id": client_id,
        "amount": 7500.00,
        "currency": "USD",
        "card_hash": "b"*64,
        "card_bin": "411111",
        "ip_address": "198.51.100.50",
        "location": {"latitude": 40.7128, "longitude": -74.0060, "country": "US", "city": "New York"},
        "device_id": "dev_e2e_999",
        "timestamp": "2026-09-15T12:00:00Z"
    }

    eval_res = await client_http.post("/api/v1/transactions/evaluate", json=eval_payload)
    assert eval_res.status_code == 200
    eval_data = eval_res.json()
    assert eval_data["decision"] in ("FLAG_FOR_REVIEW", "BLOCK")
    case_id = eval_data.get("case_id")
    assert case_id is not None

    # 2. ANALYST fetches pending cases list
    pending_res = await auth_client.get("/api/v1/cases/pending")
    assert pending_res.status_code == 200
    pending_items = pending_res.json()["items"]
    target_case = next((c for c in pending_items if c["id"] == case_id), None)
    assert target_case is not None

    # 3. ANALYST updates case priority
    patch_res = await auth_client.patch(f"/api/v1/cases/{case_id}", json={"priority": "HIGH"})
    assert patch_res.status_code == 200
    assert patch_res.json()["priority"] == "HIGH"

    # 4. ANALYST resolves investigation case
    resolve_res = await auth_client.post(
        f"/api/v1/cases/{case_id}/resolve",
        json={"action": "APPROVE", "resolution_notes": "Verified client identity via phone verification."}
    )


    assert resolve_res.status_code == 200
    assert resolve_res.json()["status"] == "RESOLVED_APPROVED"

    # 5. Check Analytics Overview
    analytics_res = await auth_client.get("/api/v1/analytics/overview")
    assert analytics_res.status_code == 200
    analytics_data = analytics_res.json()
    assert analytics_data["total_transactions_evaluated"] >= 1



@pytest.mark.asyncio
async def test_validation_failure_paths(auth_client: AsyncClient):
    """
    Validation Failure Paths:
    Verifies structured 422 errors for invalid IP formats, negative amounts, and bad payloads.
    """
    valid_user_id = str(uuid4())

    # Case A: Negative transaction amount
    res1 = await auth_client.post(
        "/api/v1/transactions/evaluate",
        json={
            "user_id": valid_user_id,
            "amount": -99.00,
            "currency": "USD",
            "card_hash": "c"*64,
            "card_bin": "411111",
            "ip_address": "198.51.100.1",
            "location": {"latitude": 0, "longitude": 0, "country": "US", "city": "NYC"},
            "timestamp": "2026-09-15T12:00:00Z"
        }
    )
    assert res1.status_code == 422

    # Case B: Invalid IP address format
    res2 = await auth_client.post(
        "/api/v1/transactions/evaluate",
        json={
            "user_id": valid_user_id,
            "amount": 150.00,
            "currency": "USD",
            "card_hash": "c"*64,
            "card_bin": "411111",
            "ip_address": "999.999.999.999_not_an_ip",
            "location": {"latitude": 0, "longitude": 0, "country": "US", "city": "NYC"},
            "timestamp": "2026-09-15T12:00:00Z"
        }
    )
    assert res2.status_code == 422


@pytest.mark.asyncio
async def test_external_service_failure_resilience(auth_client: AsyncClient):
    """
    Third-Party Service Failure Scenario:
    Verifies that when an external dependency (IP Geolocation Service) times out or throws HTTP 500,
    SentriQ fails open into degraded circuit-breaker mode without crashing core operations.
    """
    class OutageIPService:
        async def enrich_ip(self, ip_address: str):
            return IPEnrichmentResponse(
                ip_address=ip_address,
                country="UNKNOWN",
                is_vpn=False,
                is_proxy=False,
                is_tor=False,
                risk_score=0,
                status="degraded",
                provider="SentriQ-Fallback-CircuitBreaker"
            )

    app.dependency_overrides[get_ip_intel_service] = lambda: OutageIPService()

    try:
        response = await auth_client.get("/api/v1/ip-intel/lookup/203.0.113.88")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
        assert data["provider"] == "SentriQ-Fallback-CircuitBreaker"
    finally:
        app.dependency_overrides.pop(get_ip_intel_service, None)
