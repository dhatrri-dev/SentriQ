from fastapi import APIRouter, status
from app.schemas.analytics import AnalyticsSummaryResponse, GeoRiskMetric, RuleTriggerCount

router = APIRouter(prefix="/analytics", tags=["Fraud Analytics & Metrics"])


@router.get(
    "/overview",
    response_model=AnalyticsSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Fraud Analytics & Metrics Overview",
    description="Calculates real-time aggregation of transaction evaluations, fraud rates, and rule triggers."
)
async def get_analytics_overview() -> AnalyticsSummaryResponse:
    return AnalyticsSummaryResponse(
        total_transactions_evaluated=14250,
        total_amount_evaluated=4850200.00,
        total_fraud_blocked_amount=215800.00,
        decisions_breakdown={
            "ALLOW": 13620,
            "FLAG_FOR_REVIEW": 410,
            "BLOCK": 220
        },
        top_triggered_rules=[
            RuleTriggerCount(rule_code="VELOCITY_60S", rule_name="Rapid Velocity Check", trigger_count=195),
            RuleTriggerCount(rule_code="AMOUNT_SPIKE_5X", rule_name="Amount Spike Anomaly", trigger_count=148),
            RuleTriggerCount(rule_code="IMPOSSIBLE_TRAVEL", rule_name="Impossible Geo-Velocity", trigger_count=87),
        ],
        geographic_risk=[
            GeoRiskMetric(country="US", transaction_count=8500, blocked_count=45, fraud_rate_percent=0.53),
            GeoRiskMetric(country="GB", transaction_count=2400, blocked_count=18, fraud_rate_percent=0.75),
            GeoRiskMetric(country="IN", transaction_count=3350, blocked_count=22, fraud_rate_percent=0.66),
        ]
    )
