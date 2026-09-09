from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr = Field(..., description="Valid user email address")
    password: str = Field(..., min_length=6, max_length=100, description="Raw user password (at least 6 chars)")
    full_name: Optional[str] = Field(default=None, max_length=255, description="Full name")
    role: str = Field(default="ANALYST", description="Role: ANALYST, ADMIN, or CLIENT")


class LoginRequest(BaseModel):
    email: EmailStr = Field(..., description="Registered user email address")
    password: str = Field(..., description="User password")


class UserAuthResponse(BaseModel):
    id: UUID = Field(..., description="Unique User ID")
    email: EmailStr = Field(..., description="User email address")
    full_name: Optional[str] = Field(default=None, description="Full name")
    role: str = Field(default="ANALYST", description="User role")
    is_active: bool = Field(default=True, description="Account active status")
    created_at: datetime = Field(..., description="Account creation timestamp")

    model_config = {
        "from_attributes": True
    }


class TokenResponse(BaseModel):
    access_token: str = Field(..., description="JWT bearer access token string")
    token_type: str = Field(default="bearer", description="Token authorization scheme")
    expires_in_seconds: int = Field(..., description="Token validity window in seconds")
    user: UserAuthResponse = Field(..., description="Authenticated user profile details")
