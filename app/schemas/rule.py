from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field
from app.schemas.common import RuleTypeEnum


class RuleBase(BaseModel):
    rule_code: str = Field(..., min_length=3, max_length=50, description="Unique uppercase rule code (e.g. VELOCITY_60S)")
    name: str = Field(..., min_length=3, max_length=100, description="Human readable rule name")
    rule_type: RuleTypeEnum = Field(..., description="Category of the rule")
    threshold_value: float = Field(..., ge=0, description="Threshold limit value (e.g. 3.0 for 3 transactions, 5.0 for 5x spend)")
    weight_points: int = Field(..., ge=1, le=100, description="Penalty points added to risk score if triggered (1-100)")
    is_active: bool = Field(default=True, description="Whether the rule is currently active in the engine")
    description: Optional[str] = Field(default=None, max_length=500, description="Detailed explanation of rule purpose")


class RuleCreate(RuleBase):
    pass


class RuleUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=3, max_length=100)
    threshold_value: Optional[float] = Field(default=None, ge=0)
    weight_points: Optional[int] = Field(default=None, ge=1, le=100)
    is_active: Optional[bool] = Field(default=None)
    description: Optional[str] = Field(default=None, max_length=500)


class RuleResponse(RuleBase):
    id: UUID = Field(..., description="Unique rule ID")
    created_at: datetime = Field(..., description="Timestamp of rule creation")
    updated_at: Optional[datetime] = Field(default=None, description="Timestamp of last rule update")

    model_config = {
        "from_attributes": True
    }
