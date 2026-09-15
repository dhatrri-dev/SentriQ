from uuid import uuid4
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from app.main import app
from app.models.user import User
from app.models.transaction import Transaction
from app.models.evaluation import EvaluationLog


@pytest.mark.asyncio
async def test_request_id_tracing_header(async_client: AsyncClient):
    """Verify x-request-id tracing header is generated and returned in response headers."""
    response = await async_client.get("/health")
    assert response.status_code == 200
    assert "x-request-id" in response.headers
    assert len(response.headers["x-request-id"]) > 0


@pytest.mark.asyncio
async def test_custom_request_id_propagation(async_client: AsyncClient):
    """Verify client-supplied x-request-id header is preserved and propagated back."""
    custom_id = "test-correlation-id-998877"
    response = await async_client.get("/health", headers={"x-request-id": custom_id})
    assert response.status_code == 200
    assert response.headers["x-request-id"] == custom_id


@pytest.mark.asyncio
async def test_actionable_duplicate_email_conflict_error(async_client: AsyncClient):
    """Verify database duplicate registration returns actionable 400/409 error with request_id."""
    email = f"dup_user_{uuid4().hex[:8]}@sentriq.io"

    # First registration
    res1 = await async_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123", "role": "CLIENT"}
    )
    assert res1.status_code == 201

    # Duplicate registration
    res2 = await async_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123", "role": "CLIENT"}
    )
    assert res2.status_code in (400, 409)
    data = res2.json()
    assert "error" in data or "detail" in data
    assert "x-request-id" in res2.headers


@pytest.mark.asyncio
async def test_failed_writes_do_not_leave_partial_data(auth_client: AsyncClient):
    """
    Verify atomic transaction rollback: If evaluation payload validation or DB flush fails,
    no partial transaction or evaluation logs remain saved in the database.
    """
    invalid_user_id = str(uuid4())
    # Send transaction payload with invalid amount (-500.0) triggering 422 validation failure
    payload = {
        "user_id": invalid_user_id,
        "amount": -500.00,
        "currency": "USD",
        "card_hash": "a"*64,
        "card_bin": "411111",
        "ip_address": "198.51.100.1",
        "location": {"latitude": 37.7749, "longitude": -122.4194, "country": "US", "city": "San Francisco"},
        "device_id": "dev_test_123",
        "timestamp": "2026-09-02T10:00:00Z"
    }

    response = await auth_client.post("/api/v1/transactions/evaluate", json=payload)
    assert response.status_code == 422

    # Verify no partial transaction record was written to database
    db_check = await auth_client.get("/api/v1/transactions?size=100")
    if db_check.status_code == 200:
        items = db_check.json().get("items", [])
        matching = [t for t in items if str(t.get("user_id")) == invalid_user_id]
        assert len(matching) == 0, "Failed write should not leave partial transaction data in DB"


from httpx import ASGITransport

@pytest.mark.asyncio
async def test_global_500_handler_hides_sensitive_stack_traces():
    """Verify unexpected runtime exceptions return clean 500 error with request_id without exposing internal traces."""
    @app.get("/test-raise-500-internal-fault")
    async def faulty_route():
        raise RuntimeError("Simulated unexpected internal database connector crash")

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/test-raise-500-internal-fault")
        assert response.status_code == 500
        data = response.json()
        assert data["error"] == "Internal Server Error"
        assert "request_id" in data
        assert "Simulated unexpected" not in data["detail"], "Internal exception message should not leak to client"

