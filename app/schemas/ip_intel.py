from typing import Optional
from pydantic import BaseModel, Field


class IPEnrichmentResponse(BaseModel):
    ip_address: str = Field(..., description="Target IPv4 or IPv6 address evaluated")
    country: str = Field(default="UNKNOWN", description="Country code (ISO 3166-1 alpha-2)")
    city: Optional[str] = Field(default=None, description="City location name if resolved")
    isp: Optional[str] = Field(default=None, description="Internet Service Provider name")
    is_vpn: bool = Field(default=False, description="True if IP is an identified commercial VPN exit node")
    is_proxy: bool = Field(default=False, description="True if IP is an open web proxy")
    is_tor: bool = Field(default=False, description="True if IP is a Tor exit relay")
    risk_score: int = Field(default=0, ge=0, le=100, description="External service risk penalty (0-100)")
    status: str = Field(default="ok", description="Service lookup status: 'ok' or 'degraded'")
    provider: str = Field(default="MaxMind-GeoIP2-Adapter", description="Name of external service boundary provider")

    model_config = {
        "json_schema_extra": {
            "example": {
                "ip_address": "198.51.100.42",
                "country": "US",
                "city": "San Jose",
                "isp": "Cloud Provider Inc",
                "is_vpn": True,
                "is_proxy": False,
                "is_tor": False,
                "risk_score": 45,
                "status": "ok",
                "provider": "MaxMind-GeoIP2-Adapter"
            }
        }
    }
