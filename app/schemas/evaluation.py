from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field
from app.schemas.common import DecisionEnum
from app.schemas.transaction import TransactionCreate


class RuleResultItem(BaseModel):
    rule_code: str = Field(..., description="Unique rule identifier (e.g. VELOCITY_60S, AMOUNT_SPIKE_5X)")
    rule_name: str = Field(..., description="Human-readable rule name")
    points_assigned: int = Field(..., ge=0, le=100, description="Risk penalty points contributed by this rule")
    reason: str = Field(..., description="Detailed explanation of why the rule fired")


class TransactionEvaluationRequest(TransactionCreate):
    pass


class TransactionEvaluationResponse(BaseModel):
    transaction_id: UUID = Field(..., description="Assigned unique transaction ID")
    user_id: UUID = Field(..., description="User ID evaluated")
    risk_score: int = Field(..., ge=0, le=100, description="Calculated composite risk score (0-100)")
    decision: DecisionEnum = Field(..., description="Evaluation decision: ALLOW, FLAG_FOR_REVIEW, or BLOCK")
    rules_triggered: List[RuleResultItem] = Field(default_factory=list, description="List of specific fraud rules that fired")
    case_id: Optional[UUID] = Field(default=None, description="Generated case ID if flagged for analyst review")
    execution_time_ms: float = Field(..., description="Evaluation execution time in milliseconds")
    evaluated_at: datetime = Field(..., description="UTC evaluation timestamp")

    model_config = {
        "json_schema_extra": {
            "example": {
                "transaction_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
                "user_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "risk_score": 85,
                "decision": "BLOCK",
                "rules_triggered": [
                    {
                        "rule_code": "AMOUNT_SPIKE_5X",
                        "rule_name": "Amount Spike Anomaly",
                        "points_assigned": 50,
                        "reason": "Transaction amount $2,500.00 exceeds 5x user's 30-day average ($350.00)"
                    },
                    {
                        "rule_code": "IMPOSSIBLE_TRAVEL",
                        "rule_name": "Impossible Geo-Velocity",
                        "points_assigned": 35,
                        "reason": "Physical distance is 5,585 km within 12 minutes (Speed: 27,925 km/h)"
                    }
                ],
                "case_id": None,
                "execution_time_ms": 7.82,
                "evaluated_at": "2026-09-02T10:00:00Z"
            }
        }
    }
