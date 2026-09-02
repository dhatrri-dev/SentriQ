from datetime import datetime, timezone
from uuid import uuid4
from fastapi import APIRouter, status
from app.schemas.evaluation import TransactionEvaluationRequest, TransactionEvaluationResponse
from app.schemas.common import DecisionEnum, ErrorResponse

router = APIRouter(prefix="/transactions", tags=["Transactions & Evaluation"])


@router.post(
    "/evaluate",
    response_model=TransactionEvaluationResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Transaction successfully evaluated"},
        422: {"model": ErrorResponse, "description": "Validation Error (invalid IP, negative amount, etc.)"},
        500: {"model": ErrorResponse, "description": "Internal Engine Error"},
    },
    summary="Evaluate Transaction in Real-Time",
    description="Accepts a transaction payload and runs behavioral/statistical risk rules returning a risk score (0-100) and decision."
)
async def evaluate_transaction(
    payload: TransactionEvaluationRequest
) -> TransactionEvaluationResponse:
    # Contract response stub (to be connected to database & engine in Day 3 & 4)
    # Default baseline score for valid request contract
    risk_score = 15
    decision = DecisionEnum.ALLOW
    rules_triggered = []

    # Mock high-risk trigger demonstration for amount >= 5000
    if payload.amount >= 5000:
        risk_score = 85
        decision = DecisionEnum.BLOCK
        rules_triggered.append({
            "rule_code": "AMOUNT_SPIKE_5X",
            "rule_name": "Amount Spike Anomaly",
            "points_assigned": 85,
            "reason": f"Transaction amount ${payload.amount} exceeds high-risk threshold ($5,000.00)"
        })

    return TransactionEvaluationResponse(
        transaction_id=uuid4(),
        user_id=payload.user_id,
        risk_score=risk_score,
        decision=decision,
        rules_triggered=rules_triggered,
        case_id=uuid4() if decision == DecisionEnum.FLAG_FOR_REVIEW else None,
        execution_time_ms=4.12,
        evaluated_at=datetime.now(timezone.utc)
    )
