from unittest.mock import AsyncMock, patch
import httpx
import pytest
from httpx import AsyncClient, Response

from app.main import app
from app.schemas.ip_intel import IPEnrichmentResponse
from app.services.ip_intel import IPIntelligenceService, get_ip_intel_service


@pytest.mark.asyncio
async def test_ip_intel_service_success_lookup():
    """Verify IPIntelligenceService parses successful 200 OK external response correctly."""
    mock_payload = {
        "ip_address": "198.51.100.42",
        "country": "US",
        "city": "San Jose",
        "isp": "Test Provider Inc",
        "is_vpn": True,
        "is_proxy": False,
        "is_tor": False,
        "risk_score": 40,
        "status": "ok",
        "provider": "MaxMind-GeoIP2-Adapter"
    }

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    req = httpx.Request("GET", "https://api.ip-intel.internal/v1/lookup/198.51.100.42")
    mock_response = Response(200, json=mock_payload, request=req)

    mock_client.get.return_value = mock_response

    service = IPIntelligenceService(
        base_url="https://api.ip-intel.internal",
        timeout_seconds=3.0,
        api_key="test_key",
        client=mock_client
    )

    result = await service.enrich_ip("198.51.100.42")
    assert isinstance(result, IPEnrichmentResponse)
    assert result.ip_address == "198.51.100.42"
    assert result.country == "US"
    assert result.is_vpn is True
    assert result.risk_score == 40
    assert result.status == "ok"


@pytest.mark.asyncio
async def test_ip_intel_service_timeout_fallback():
    """Verify timeout exception triggers graceful degraded fallback without raising error."""
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.side_effect = httpx.TimeoutException("Connection timed out after 3.0s")

    service = IPIntelligenceService(
        base_url="https://api.ip-intel.internal",
        timeout_seconds=3.0,
        api_key="test_key",
        client=mock_client
    )

    result = await service.enrich_ip("203.0.113.1")
    assert result.ip_address == "203.0.113.1"
    assert result.status == "degraded"
    assert result.provider == "SentriQ-Fallback-CircuitBreaker"
    assert result.country == "UNKNOWN"
    assert result.is_vpn is False


@pytest.mark.asyncio
async def test_ip_intel_service_http_error_fallback():
    """Verify external HTTP 500 error returns degraded fallback response gracefully."""
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    req = httpx.Request("GET", "https://api.ip-intel.internal/v1/lookup/203.0.113.5")
    mock_client.get.side_effect = httpx.HTTPStatusError("500 Server Error", request=req, response=Response(500))

    service = IPIntelligenceService(client=mock_client)
    result = await service.enrich_ip("203.0.113.5")
    assert result.status == "degraded"
    assert result.provider == "SentriQ-Fallback-CircuitBreaker"


@pytest.mark.asyncio
async def test_ip_intel_endpoint_authenticated(auth_client: AsyncClient):
    """Verify GET /api/v1/ip-intel/lookup/{ip_address} returns enriched IP payload for ANALYST user."""
    mock_response_data = IPEnrichmentResponse(
        ip_address="198.51.100.99",
        country="DE",
        city="Frankfurt",
        isp="Hetzner Online",
        is_vpn=False,
        is_proxy=False,
        is_tor=False,
        risk_score=10,
        status="ok",
        provider="MaxMind-Mocked"
    )

    class MockedIPService:
        async def enrich_ip(self, ip_address: str):
            return mock_response_data

    app.dependency_overrides[get_ip_intel_service] = lambda: MockedIPService()

    try:
        response = await auth_client.get("/api/v1/ip-intel/lookup/198.51.100.99")
        assert response.status_code == 200
        data = response.json()
        assert data["ip_address"] == "198.51.100.99"
        assert data["country"] == "DE"
        assert data["city"] == "Frankfurt"
        assert data["provider"] == "MaxMind-Mocked"
    finally:
        app.dependency_overrides.pop(get_ip_intel_service, None)


@pytest.mark.asyncio
async def test_ip_intel_endpoint_unauthorized(async_client: AsyncClient):
    """Verify unauthenticated requests receive 401 Unauthorized status."""
    response = await async_client.get("/api/v1/ip-intel/lookup/198.51.100.99")
    assert response.status_code == 401
