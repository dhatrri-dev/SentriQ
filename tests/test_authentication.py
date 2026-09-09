"""Day 7 – Authentication Tests
Tests verify:
  * User registration creates account and returns valid JWT token
  * Duplicate email registration returns 400
  * Weak password (< 6 chars) returns 422 validation error
  * Login with valid credentials returns token
  * Login with invalid credentials returns 401 Unauthorized
  * Protected /auth/me returns current user when token is valid
  * Protected /auth/me returns 401 without a token
  * Protected write endpoints (rules, blocklist) reject anonymous requests (401)
  * Secrets are not exposed in responses
"""
import pytest
from uuid import uuid4
from httpx import AsyncClient
from tests.db_fixtures import setup_test_database, db_session  # noqa: F401


# ---------------------------------------------------------------------------
# Registration Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_register_creates_user_and_returns_token(async_client: AsyncClient):
    """POST /auth/register creates a new user and returns a signed JWT token."""
    payload = {
        "email": f"analyst_{uuid4().hex[:8]}@sentriq.io",
        "password": "secure_password_123",
        "full_name": "Test Analyst",
        "role": "ANALYST"
    }
    res = await async_client.post("/api/v1/auth/register", json=payload)
    assert res.status_code == 201
    data = res.json()

    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert "expires_in_seconds" in data
    assert data["expires_in_seconds"] > 0
    assert "user" in data
    assert data["user"]["email"] == payload["email"]
    assert data["user"]["role"] == "ANALYST"
    assert data["user"]["is_active"] is True

    # Ensure password hash is never exposed
    assert "hashed_password" not in data
    assert "password" not in data["user"]


@pytest.mark.asyncio
async def test_register_duplicate_email_returns_400(async_client: AsyncClient):
    """POST /auth/register with an already registered email returns 400."""
    payload = {
        "email": f"duplicate_{uuid4().hex[:8]}@sentriq.io",
        "password": "pass123456",
    }
    first = await async_client.post("/api/v1/auth/register", json=payload)
    assert first.status_code == 201

    second = await async_client.post("/api/v1/auth/register", json=payload)
    assert second.status_code == 400
    assert "already registered" in second.json()["detail"].lower()


@pytest.mark.asyncio
async def test_register_weak_password_returns_422(async_client: AsyncClient):
    """POST /auth/register with short password (< 6 chars) returns 422 Validation Error."""
    payload = {
        "email": f"weak_{uuid4().hex[:8]}@sentriq.io",
        "password": "abc",  # too short
    }
    res = await async_client.post("/api/v1/auth/register", json=payload)
    assert res.status_code == 422


# ---------------------------------------------------------------------------
# Login Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_login_valid_credentials_returns_token(async_client: AsyncClient):
    """POST /auth/login with correct credentials returns a valid JWT."""
    email = f"login_{uuid4().hex[:8]}@sentriq.io"
    password = "login_pass_secure"

    # Register first
    await async_client.post("/api/v1/auth/register", json={"email": email, "password": password})

    # Login
    res = await async_client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == email


@pytest.mark.asyncio
async def test_login_wrong_password_returns_401(async_client: AsyncClient):
    """POST /auth/login with incorrect password returns 401 Unauthorized."""
    email = f"wrong_{uuid4().hex[:8]}@sentriq.io"
    await async_client.post("/api/v1/auth/register", json={"email": email, "password": "correct_pass"})

    res = await async_client.post("/api/v1/auth/login", json={"email": email, "password": "wrong_password"})
    assert res.status_code == 401
    assert "invalid" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_login_unknown_email_returns_401(async_client: AsyncClient):
    """POST /auth/login with nonexistent email returns 401 Unauthorized."""
    res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@notregistered.io", "password": "somepassword"}
    )
    assert res.status_code == 401


# ---------------------------------------------------------------------------
# /auth/me Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_me_authenticated_returns_profile(async_client: AsyncClient):
    """GET /auth/me with valid Bearer token returns current user profile."""
    email = f"me_{uuid4().hex[:8]}@sentriq.io"
    reg = await async_client.post("/api/v1/auth/register", json={"email": email, "password": "mypass123"})
    assert reg.status_code == 201
    token = reg.json()["access_token"]

    res = await async_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["email"] == email
    assert "hashed_password" not in data


@pytest.mark.asyncio
async def test_get_me_unauthenticated_returns_401(async_client: AsyncClient):
    """GET /auth/me without any Bearer token returns 401 Unauthorized."""
    res = await async_client.get("/api/v1/auth/me")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_get_me_invalid_token_returns_401(async_client: AsyncClient):
    """GET /auth/me with malformed/expired token returns 401 Unauthorized."""
    res = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer this.is.not.a.valid.jwt"}
    )
    assert res.status_code == 401


# ---------------------------------------------------------------------------
# Protected Route Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_anonymous_create_rule_returns_401(async_client: AsyncClient):
    """POST /api/v1/rules without auth returns 401 Unauthorized (protected route)."""
    payload = {
        "rule_code": "ANON_ATTEMPT",
        "name": "Anonymous test rule",
        "rule_type": "VELOCITY",
        "threshold_value": 1.0,
        "weight_points": 10
    }
    res = await async_client.post("/api/v1/rules", json=payload)
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_authenticated_create_rule_succeeds(async_client: AsyncClient):
    """POST /api/v1/rules with valid Bearer token returns 201 Created."""
    # Register and get token
    email = f"rule_author_{uuid4().hex[:8]}@sentriq.io"
    reg = await async_client.post("/api/v1/auth/register", json={"email": email, "password": "secpass456"})
    token = reg.json()["access_token"]

    payload = {
        "rule_code": f"AUTH_RULE_{uuid4().hex[:6].upper()}",
        "name": "Authenticated Rule Creation Test",
        "rule_type": "AMOUNT_ANOMALY",
        "threshold_value": 2000.0,
        "weight_points": 30
    }
    res = await async_client.post(
        "/api/v1/rules",
        json=payload,
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 201
    assert res.json()["rule_code"] == payload["rule_code"]


@pytest.mark.asyncio
async def test_anonymous_add_blocklist_returns_401(async_client: AsyncClient):
    """POST /api/v1/blocklist without auth returns 401 Unauthorized."""
    payload = {
        "entity_type": "IP",
        "entity_value": "10.0.0.1",
        "reason": "Anonymous test blocklist attempt"
    }
    res = await async_client.post("/api/v1/blocklist", json=payload)
    assert res.status_code == 401
