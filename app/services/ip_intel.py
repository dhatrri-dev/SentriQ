import logging
from typing import Optional
import httpx

from app.core.config import settings
from app.schemas.ip_intel import IPEnrichmentResponse

logger = logging.getLogger(__name__)


class IPIntelligenceService:
    """
    Service-layer boundary for interacting with external IP Intelligence & Geolocation APIs.
    Guarantees strict timeout bounds, exception safety, and graceful degradation fallback.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
        api_key: Optional[str] = None,
        client: Optional[httpx.AsyncClient] = None
    ):
        self.base_url = (base_url or settings.IP_INTEL_SERVICE_URL).rstrip("/")
        self.timeout_seconds = timeout_seconds or settings.IP_INTEL_TIMEOUT_SECONDS
        self.api_key = api_key or settings.IP_INTEL_API_KEY
        self._client = client

    def _get_client(self) -> httpx.AsyncClient:
        if self._client and not self._client.is_closed:
            return self._client
        return httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout_seconds, connect=1.0),
            headers={"X-API-Key": self.api_key, "User-Agent": f"SentriQ-Engine/{settings.VERSION}"}
        )

    async def enrich_ip(self, ip_address: str) -> IPEnrichmentResponse:
        """
        Enriches an IPv4/IPv6 address with geolocation, proxy/VPN flags, and external risk scores.
        Handles timeouts and HTTP failures gracefully by returning a safe degraded fallback.
        """
        endpoint = f"{self.base_url}/v1/lookup/{ip_address}"
        client_created_here = self._client is None

        try:
            client = self._get_client()
            response = await client.get(endpoint)
            response.raise_for_status()
            data = response.json()
            return IPEnrichmentResponse.model_validate(data)

        except httpx.TimeoutException:
            logger.warning(
                f"External IP Intelligence service timed out ({self.timeout_seconds}s limit) for IP: {ip_address}. "
                "Failing open with degraded fallback response."
            )
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

        except (httpx.HTTPStatusError, httpx.RequestError, Exception) as exc:
            logger.error(
                f"External IP Intelligence service error for IP {ip_address}: {exc}. "
                "Returning safe degraded response."
            )
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

        finally:
            if client_created_here and 'client' in locals() and not client.is_closed:
                await client.aclose()


# Dependency injection provider for FastAPI
def get_ip_intel_service() -> IPIntelligenceService:
    return IPIntelligenceService()
