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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create all database tables on startup using SQLAlchemy metadata."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.PROJECT_DESCRIPTION,
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

# Set up CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
    # Include standard FastAPI detail list for backward compatibility
    res_content = error_response.model_dump()
    res_content["detail"] = exc.errors()
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=res_content
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
