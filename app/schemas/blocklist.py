from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field
from app.schemas.common import EntityTypeEnum


class BlocklistBase(BaseModel):
    entity_type: EntityTypeEnum = Field(..., description="Type of entity: IP, CARD_BIN, CARD_HASH, EMAIL_DOMAIN, COUNTRY")
    entity_value: str = Field(..., min_length=2, max_length=100, description="Value to block (e.g. 192.0.2.1, tempmail.com)")
    reason: str = Field(..., min_length=3, max_length=255, description="Reason for blocklisting")
    expires_at: Optional[datetime] = Field(default=None, description="Optional expiration timestamp for temporary bans")


class BlocklistCreate(BlocklistBase):
    pass


class BlocklistResponse(BlocklistBase):
    id: UUID = Field(..., description="Unique blocklist entry ID")
    is_active: bool = Field(default=True, description="Whether the blocklist entry is currently enforced")
    created_at: datetime = Field(..., description="Timestamp of addition")

    model_config = {
        "from_attributes": True
    }
