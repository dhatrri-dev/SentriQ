from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1.router import api_router
from app.schemas.health import HealthResponse
from app.core.database import engine, Base
import app.models  # noqa: F401 — register all ORM models


from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from app.schemas.common import ErrorDetail, ErrorResponse


from app.core.logging import setup_structured_logging
from app.core.middleware import RequestTracingMiddleware

# Initialize structured JSON logging system
setup_structured_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create all database tables on startup using SQLAlchemy metadata."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


tags_metadata = [
    {
        "name": "Authentication",
        "description": "User registration, JWT authentication token issuance, and profile retrieval.",
    },
    {
        "name": "Transactions",
        "description": "Real-time payment transaction risk evaluation, scoring, and transaction history.",
    },
    {
        "name": "Cases",
        "description": "Fraud investigation case review queue, assignment, and manual case resolution.",
    },
    {
        "name": "Rules",
        "description": "Management of behavioral fraud risk rules (velocity, anomaly, geo-distance, thresholds).",
    },
    {
        "name": "Blocklist",
        "description": "Suspicious IP addresses, email domains, and BIN blocklist enforcement.",
    },
    {
        "name": "IP Intelligence",
        "description": "External IP reputation, proxy/VPN detection, and geolocation enrichment.",
    },
    {
        "name": "Analytics",
        "description": "Fraud metrics, risk score distribution, and platform health analytics.",
    },
    {
        "name": "Health",
        "description": "Active readiness and liveness health probes for DB and external dependencies.",
    },
]

app = FastAPI(
    title="SentriQ API",
    description=(
        "## Real-Time Transaction Risk & Fraud Rule Engine\n\n"
        "SentriQ is an enterprise-grade backend system for real-time payment fraud detection, "
        "rule evaluation, IP intelligence enrichment, and investigation case management."
    ),
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    openapi_tags=tags_metadata,
    lifespan=lifespan,
)

# Set up tracing and CORS middleware
app.add_middleware(RequestTracingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



import logging
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

logger = logging.getLogger("sentriq.exceptions")


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc: RequestValidationError):
    """Custom exception handler to return structured, user-friendly 422 validation errors."""
    formatted_errors = [
        ErrorDetail(
            loc=[str(loc_item) for loc_item in err.get("loc", [])],
            msg=err.get("msg", "Invalid input field"),
            type=err.get("type", "value_error")
        )
        for err in exc.errors()
    ]
    error_response = ErrorResponse(
        error="Validation Error",
        detail="One or more request payload fields failed validation.",
        errors=formatted_errors
    )
    res_content = error_response.model_dump()
    res_content["detail"] = exc.errors()
    request_id = getattr(request.state, "request_id", None)
    headers = {"x-request-id": request_id} if request_id else {}
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=res_content,
        headers=headers
    )


@app.exception_handler(IntegrityError)
@app.exception_handler(SQLAlchemyError)
async def database_exception_handler(request, exc: SQLAlchemyError):
    """Handles database integrity and constraint errors with actionable client feedback."""
    request_id = getattr(request.state, "request_id", None)
    logger.error(
        f"Database transaction error during {request.method} {request.url.path}: {exc}",
        exc_info=True,
        extra={"request_id": request_id} if request_id else {}
    )

    is_integrity = isinstance(exc, IntegrityError)
    status_code = status.HTTP_409_CONFLICT if is_integrity else status.HTTP_400_BAD_REQUEST
    error_title = "Database Conflict Error" if is_integrity else "Database Transaction Error"
    actionable_detail = (
        "Database constraint violation occurred. Check for duplicate unique keys or invalid foreign references."
        if is_integrity else "Database transaction could not be processed. Request has been safely rolled back."
    )

    headers = {"x-request-id": request_id} if request_id else {}
    return JSONResponse(
        status_code=status_code,
        content={
            "error": error_title,
            "detail": actionable_detail,
            "request_id": request_id
        },
        headers=headers
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc: StarletteHTTPException):
    """Standardized handler for HTTP exceptions ensuring request ID propagation."""
    request_id = getattr(request.state, "request_id", None)
    headers = {"x-request-id": request_id} if request_id else {}
    
    content = {
        "error": f"HTTP {exc.status_code}",
        "detail": str(exc.detail),
    }
    if request_id:
        content["request_id"] = request_id

    return JSONResponse(
        status_code=exc.status_code,
        content=content,
        headers=headers
    )


@app.exception_handler(Exception)
async def generic_uncaught_exception_handler(request, exc: Exception):
    """Global catch-all exception handler logging unexpected errors and returning safe actionable 500 response."""
    request_id = getattr(request.state, "request_id", None)
    logger.error(
        f"Uncaught internal engine error processing {request.method} {request.url.path}: {exc}",
        exc_info=True,
        extra={"request_id": request_id} if request_id else {}
    )

    headers = {"x-request-id": request_id} if request_id else {}
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "detail": "An unexpected internal server error occurred. Please contact support with the correlation request ID.",
            "request_id": request_id
        },
        headers=headers
    )




@app.get(
    "/",
    tags=["Root"],
    summary="Root Endpoint",
    description="Welcome endpoint for the SentriQ API."
)
async def root():
    return {
        "message": f"Welcome to {settings.PROJECT_NAME} API",
        "version": settings.VERSION,
        "docs": "/docs",
        "health": "/health",
        "description": settings.PROJECT_DESCRIPTION
    }


@app.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    tags=["Health"],
    summary="Root Health Check",
    description="Direct root health endpoint."
)
async def root_health() -> HealthResponse:
    return HealthResponse(
        status="healthy",
        service=settings.PROJECT_NAME,
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
        timestamp=datetime.now(timezone.utc)
    )


# Include versioned API router
app.include_router(api_router, prefix=settings.API_V1_STR)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
