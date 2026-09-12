from fastapi import APIRouter, Depends, status

from app.core.dependencies import require_roles
from app.models.user import User
from app.schemas.ip_intel import IPEnrichmentResponse
from app.services.ip_intel import IPIntelligenceService, get_ip_intel_service

router = APIRouter(prefix="/ip-intel", tags=["IP Intelligence & Geolocation Service"])


@router.get(
    "/lookup/{ip_address}",
    response_model=IPEnrichmentResponse,
    status_code=status.HTTP_200_OK,
    summary="Lookup IP Intelligence & Risk Signals",
    description="Delegates IP geolocation and proxy/VPN risk lookup to external service boundary with automatic fallback."
)
async def lookup_ip_intelligence(
    ip_address: str,
    ip_service: IPIntelligenceService = Depends(get_ip_intel_service),
    current_user: User = Depends(require_roles("ADMIN", "ANALYST"))
) -> IPEnrichmentResponse:
    """
    Focused route endpoint delegating all external HTTP communication, timeouts,
    and resilience strategies to the IPIntelligenceService boundary layer.
    """
    return await ip_service.enrich_ip(ip_address)
