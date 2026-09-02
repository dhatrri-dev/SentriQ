from typing import Dict, List
from pydantic import BaseModel, Field


class RuleTriggerCount(BaseModel):
    rule_code: str = Field(..., description="Unique rule code")
    rule_name: str = Field(..., description="Human readable rule name")
    trigger_count: int = Field(..., ge=0, description="Total number of times triggered")


class GeoRiskMetric(BaseModel):
    country: str = Field(..., description="ISO Country Code")
    transaction_count: int = Field(..., ge=0)
    blocked_count: int = Field(..., ge=0)
    fraud_rate_percent: float = Field(..., ge=0, le=100)


class AnalyticsSummaryResponse(BaseModel):
    total_transactions_evaluated: int = Field(..., ge=0, description="Total transactions evaluated")
    total_amount_evaluated: float = Field(..., ge=0, description="Gross transaction volume evaluated")
    total_fraud_blocked_amount: float = Field(..., ge=0, description="Monetary value of blocked transactions")
    decisions_breakdown: Dict[str, int] = Field(..., description="Count of decisions by ALLOW, FLAG_FOR_REVIEW, BLOCK")
    top_triggered_rules: List[RuleTriggerCount] = Field(default_factory=list, description="Top triggered rules")
    geographic_risk: List[GeoRiskMetric] = Field(default_factory=list, description="Geographic risk metrics")
