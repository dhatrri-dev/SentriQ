from datetime import datetime, timezone
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(default="healthy", description="Application health status")
    service: str = Field(description="Service name")
    version: str = Field(description="Application version")
    environment: str = Field(description="Current deployment environment")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Current server UTC timestamp")
