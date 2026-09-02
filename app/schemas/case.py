from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field
from app.schemas.common import CasePriorityEnum, CaseStatusEnum, ResolutionActionEnum


class CaseBase(BaseModel):
    transaction_id: UUID = Field(..., description="Flagged transaction ID")
    user_id: UUID = Field(..., description="User ID involved")
    risk_score: int = Field(..., ge=0, le=100, description="Risk score at time of evaluation")
    priority: CasePriorityEnum = Field(default=CasePriorityEnum.MEDIUM, description="Investigation priority")


class CaseCreate(CaseBase):
    pass


class CaseResolveRequest(BaseModel):
    action: ResolutionActionEnum = Field(..., description="Analyst action: APPROVE or BLOCK")
    resolution_notes: str = Field(..., min_length=5, max_length=1000, description="Audit explanation for resolution decision")


class CaseResponse(CaseBase):
    id: UUID = Field(..., description="Unique case ID")
    status: CaseStatusEnum = Field(default=CaseStatusEnum.PENDING, description="Current investigation status")
    assigned_analyst_id: Optional[UUID] = Field(default=None, description="Analyst handling the case")
    resolution_notes: Optional[str] = Field(default=None, description="Notes recorded during resolution")
    resolved_at: Optional[datetime] = Field(default=None, description="Timestamp of resolution")
    created_at: datetime = Field(..., description="Timestamp of case creation")

    model_config = {
        "from_attributes": True
    }
