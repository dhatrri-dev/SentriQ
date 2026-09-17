from datetime import datetime, timezone
from pydantic import BaseModel, Field


from typing import Dict, Optional


class HealthResponse(BaseModel):
    status: str = Field(default="healthy", description="Application health status")
    service: str = Field(description="Service name")
    version: str = Field(description="Application version")
    environment: str = Field(description="Current deployment environment")
    dependencies: Optional[Dict[str, str]] = Field(default=None, description="Active status of sub-system dependencies (database, external services)")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Current server UTC timestamp")

