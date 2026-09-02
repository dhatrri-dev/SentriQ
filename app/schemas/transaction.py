from datetime import datetime, timezone
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, IPvAnyAddress


class LocationSchema(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Latitude coordinate between -90 and 90")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Longitude coordinate between -180 and 180")
    country: str = Field(..., min_length=2, max_length=3, description="ISO country code (e.g. US, IN, GBR)")
    city: Optional[str] = Field(default=None, description="City name")


class TransactionBase(BaseModel):
    user_id: UUID = Field(..., description="Unique user/customer identifier")
    card_hash: str = Field(..., min_length=16, description="Tokenized/hashed card identifier")
    card_bin: Optional[str] = Field(default=None, min_length=6, max_length=8, description="Bank Identification Number (first 6-8 digits)")
    amount: float = Field(..., gt=0, description="Transaction amount (must be positive)")
    currency: str = Field(default="USD", min_length=3, max_length=3, description="3-letter currency code (ISO 4217)")
    ip_address: IPvAnyAddress = Field(..., description="IPv4 or IPv6 address of transaction origin")
    location: LocationSchema = Field(..., description="Geographic location details")
    device_id: Optional[str] = Field(default=None, description="Unique device fingerprint ID")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="UTC timestamp of the transaction")


class TransactionCreate(TransactionBase):
    pass


class TransactionResponse(TransactionBase):
    id: UUID = Field(..., description="Unique transaction ID")
    risk_score: Optional[int] = Field(default=None, ge=0, le=100, description="Evaluated risk score (0-100)")
    status: str = Field(default="PENDING", description="Transaction status (APPROVED, FLAGGED, BLOCKED)")
    created_at: datetime = Field(..., description="Record creation timestamp")

    model_config = {
        "from_attributes": True
    }
