from datetime import datetime, timezone
import time
from typing import Optional
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.user import User
from app.models.transaction import Transaction
from app.models.evaluation import EvaluationLog, EvaluationLogItem
from app.models.case import InvestigationCase
from app.models.blocklist import BlocklistEntity
from app.models.rule import RiskRule
from app.schemas.evaluation import RuleResultItem, TransactionEvaluationRequest, TransactionEvaluationResponse
from app.schemas.transaction import LocationSchema, TransactionResponse
from app.schemas.common import CasePriorityEnum, CaseStatusEnum, DecisionEnum, ErrorResponse, PaginatedResponse

router = APIRouter(prefix="/transactions", tags=["Transactions & Evaluation"])



@router.post(
    "/evaluate",
    response_model=TransactionEvaluationResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Transaction successfully evaluated"},
        400: {"model": ErrorResponse, "description": "Bad Request"},
        422: {"model": ErrorResponse, "description": "Validation Error (invalid IP, negative amount, etc.)"},
        500: {"model": ErrorResponse, "description": "Internal Engine Error"},
    },
    summary="Evaluate Transaction in Real-Time",
    description="Accepts a transaction payload, validates input, runs fraud risk rules, persists transaction & logs to DB, and returns evaluation decision."
)
async def evaluate_transaction(
    payload: TransactionEvaluationRequest,
    db: AsyncSession = Depends(get_db)
) -> TransactionEvaluationResponse:
    start_time = time.perf_counter()

    # 1. Ensure User exists or auto-create test user
    user_stmt = select(User).where(User.id == payload.user_id)
    result = await db.execute(user_stmt)
    user = result.scalar_one_or_none()

    if not user:
        user = User(
            id=payload.user_id,
            email=f"user_{payload.user_id.hex[:8]}@example.com",
            full_name="Evaluated User",
            role="CLIENT",
            avg_monthly_spend=500.00,
            total_transaction_count=1
        )
        db.add(user)
        await db.flush()

    # 2. Check Blocklist entities (ip_address, card_hash, device_id)
    block_stmt = select(BlocklistEntity).where(
        BlocklistEntity.is_active == True,
        BlocklistEntity.entity_value.in_([
            str(payload.ip_address),
            payload.card_hash,
            payload.device_id or ""
        ])
    )
    block_result = await db.execute(block_stmt)
    block_entry = block_result.scalar_one_or_none()

    rules_triggered = []
    risk_score = 15

    if block_entry:
        risk_score = 100
        rules_triggered.append(RuleResultItem(
            rule_code="BLOCKLIST_MATCH",
            rule_name="Entity Blocklisted",
            points_assigned=100,
            reason=f"Matched active blocklist entry ({block_entry.entity_type}): {block_entry.reason}"
        ))
    else:
        # Check active rules from database
        active_rules_stmt = select(RiskRule).where(RiskRule.is_active == True)
        active_rules_res = await db.execute(active_rules_stmt)
        active_rules = active_rules_res.scalars().all()

        for rule in active_rules:
            if rule.rule_type == "AMOUNT_ANOMALY" and payload.amount >= rule.threshold_value:
                risk_score += rule.weight_points
                rules_triggered.append(RuleResultItem(
                    rule_code=rule.rule_code,
                    rule_name=rule.name,
                    points_assigned=rule.weight_points,
                    reason=f"Transaction amount ${payload.amount:.2f} exceeds rule threshold (${rule.threshold_value:.2f})"
                ))

        # Fallback high-risk trigger for amount >= 5000 if no db rule matched
        if payload.amount >= 5000 and not any(r.rule_code == "AMOUNT_SPIKE_5X" for r in rules_triggered):
            points = 85
            risk_score = max(risk_score, points)
            rules_triggered.append(RuleResultItem(
                rule_code="AMOUNT_SPIKE_5X",
                rule_name="Amount Spike Anomaly",
                points_assigned=points,
                reason=f"Transaction amount ${payload.amount:.2f} exceeds high-risk threshold ($5,000.00)"
            ))

    risk_score = min(100, max(0, risk_score))

    if risk_score >= 75:
        decision = DecisionEnum.BLOCK
    elif risk_score >= 40:
        decision = DecisionEnum.FLAG_FOR_REVIEW
    else:
        decision = DecisionEnum.ALLOW

    # 3. Save Transaction
    tx_id = uuid4()
    transaction = Transaction(
        id=tx_id,
        user_id=payload.user_id,
        card_hash=payload.card_hash,
        card_bin=payload.card_bin,
        amount=payload.amount,
        currency=payload.currency,
        ip_address=str(payload.ip_address),
        latitude=payload.location.latitude,
        longitude=payload.location.longitude,
        country=payload.location.country,
        city=payload.location.city,
        device_id=payload.device_id,
        status=decision.value,
        risk_score=risk_score,
        timestamp=payload.timestamp
    )
    db.add(transaction)

    # 4. Save Evaluation Log
    exec_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
    eval_log_id = uuid4()
    eval_log = EvaluationLog(
        id=eval_log_id,
        transaction_id=tx_id,
        final_score=risk_score,
        decision=decision.value,
        rules_triggered_count=len(rules_triggered),
        execution_time_ms=exec_time_ms,
        evaluated_at=datetime.now(timezone.utc)
    )
    db.add(eval_log)

    # 5. Save Evaluation Log Items
    for item in rules_triggered:
        log_item = EvaluationLogItem(
            id=uuid4(),
            evaluation_log_id=eval_log_id,
            rule_code=item.rule_code,
            points_assigned=item.points_assigned,
            reason=item.reason
        )
        db.add(log_item)

    # 6. Save Investigation Case if flagged or blocked
    case_id = None
    if decision in (DecisionEnum.FLAG_FOR_REVIEW, DecisionEnum.BLOCK):
        case_id = uuid4()
        priority = CasePriorityEnum.HIGH if decision == DecisionEnum.BLOCK else CasePriorityEnum.MEDIUM
        case = InvestigationCase(
            id=case_id,
            transaction_id=tx_id,
            user_id=payload.user_id,
            risk_score=risk_score,
            status=CaseStatusEnum.PENDING.value,
            priority=priority.value
        )
        db.add(case)

    await db.flush()

    return TransactionEvaluationResponse(
        transaction_id=tx_id,
        user_id=payload.user_id,
        risk_score=risk_score,
        decision=decision,
        rules_triggered=rules_triggered,
        case_id=case_id,
        execution_time_ms=exec_time_ms,
        evaluated_at=eval_log.evaluated_at
    )


def _map_transaction_response(tx: Transaction) -> TransactionResponse:
    return TransactionResponse(
        id=tx.id,
        user_id=tx.user_id,
        card_hash=tx.card_hash,
        card_bin=tx.card_bin,
        amount=float(tx.amount),
        currency=tx.currency,
        ip_address=tx.ip_address,
        location=LocationSchema(
            latitude=tx.latitude,
            longitude=tx.longitude,
            country=tx.country,
            city=tx.city
        ),
        device_id=tx.device_id,
        timestamp=tx.timestamp,
        risk_score=tx.risk_score,
        status=tx.status,
        created_at=tx.created_at
    )


@router.get(
    "",
    response_model=PaginatedResponse[TransactionResponse],
    status_code=status.HTTP_200_OK,
    summary="List transactions (Paginated)",
    description="Returns a paginated list of evaluated transactions sorted with stable ordering (newest first)."
)
async def list_transactions(
    page: int = Query(default=1, ge=1, description="Page number"),
    size: int = Query(default=20, ge=1, le=100, description="Page size limit"),
    user_id: Optional[UUID] = Query(default=None, description="Filter by User ID"),
    status_filter: Optional[str] = Query(default=None, alias="status", description="Filter by status (ALLOW, FLAGGED, BLOCK)"),
    db: AsyncSession = Depends(get_db)
) -> PaginatedResponse[TransactionResponse]:
    from sqlalchemy import func
    from app.schemas.common import PaginatedResponse

    query = select(Transaction)
    if user_id:
        query = query.where(Transaction.user_id == user_id)
    if status_filter:
        query = query.where(Transaction.status == status_filter.upper())

    # Stable ordering: newest timestamp first, tie breaker on unique primary key id
    query = query.order_by(Transaction.timestamp.desc(), Transaction.id.desc())

    # Count total matching
    count_query = select(func.count()).select_from(query.subquery())
    total_count = (await db.execute(count_query)).scalar() or 0

    # Paginate
    paginated_query = query.offset((page - 1) * size).limit(size)
    result = await db.execute(paginated_query)
    transactions = result.scalars().all()

    items = [_map_transaction_response(tx) for tx in transactions]
    return PaginatedResponse[TransactionResponse](
        total=total_count,
        page=page,
        size=size,
        items=items
    )


@router.get(
    "/{transaction_id}",
    response_model=TransactionResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Transaction details found"},
        404: {"model": ErrorResponse, "description": "Transaction not found"},
    },
    summary="Get transaction detail",
    description="Retrieves a single transaction record by its unique ID."
)
async def get_transaction_detail(
    transaction_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> TransactionResponse:
    stmt = select(Transaction).where(Transaction.id == transaction_id)
    result = await db.execute(stmt)
    transaction = result.scalar_one_or_none()

    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction with ID {transaction_id} not found"
        )

    return _map_transaction_response(transaction)


