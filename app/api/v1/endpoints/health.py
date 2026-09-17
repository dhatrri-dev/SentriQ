from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Response, status

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.schemas.health import HealthResponse
from app.core.config import settings
from app.services.ip_intel import IPIntelligenceService, get_ip_intel_service

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Comprehensive Service & Dependency Health Check",
    description="Probes database connectivity and external service dependencies, returning 200 OK if healthy or 503 if unhealthy."
)
async def check_health(
    response: Response,
    db: AsyncSession = Depends(get_db),
    ip_service: IPIntelligenceService = Depends(get_ip_intel_service)
) -> HealthResponse:
    dependencies_status = {}
    is_healthy = True

    # 1. Probe Database Connection
    try:
        await db.execute(text("SELECT 1"))
        dependencies_status["database"] = "healthy"
    except Exception as exc:
        dependencies_status["database"] = f"unhealthy: {str(exc)}"
        is_healthy = False

    # 2. Probe External IP Intelligence Service
    try:
        intel_res = await ip_service.enrich_ip("127.0.0.1")
        dependencies_status["ip_intel_service"] = intel_res.status
    except Exception:
        dependencies_status["ip_intel_service"] = "degraded"

    if not is_healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return HealthResponse(
        status="healthy" if is_healthy else "unhealthy",
        service=settings.PROJECT_NAME,
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
        dependencies=dependencies_status,
        timestamp=datetime.now(timezone.utc)
    )

