from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_roles
from app.models.rule import RiskRule
from app.models.user import User
from app.schemas.rule import RuleCreate, RuleResponse, RuleUpdate
from app.schemas.common import ErrorResponse, RuleTypeEnum

router = APIRouter(prefix="/rules", tags=["Risk Rules"])

DEFAULT_SEED_RULES = [
    {
        "id": UUID("11111111-1111-1111-1111-111111111111"),
        "rule_code": "VELOCITY_60S",
        "name": "Rapid Transaction Velocity",
        "rule_type": RuleTypeEnum.VELOCITY.value,
        "threshold_value": 3.0,
        "weight_points": 40,
        "is_active": True,
        "description": "Flags >3 transactions on same card in 60s window.",
    },
    {
        "id": UUID("22222222-2222-2222-2222-222222222222"),
        "rule_code": "AMOUNT_SPIKE_5X",
        "name": "Amount Spike Anomaly",
        "rule_type": RuleTypeEnum.AMOUNT_ANOMALY.value,
        "threshold_value": 5000.0,
        "weight_points": 50,
        "is_active": True,
        "description": "Flags transactions exceeding high amount threshold.",
    },
    {
        "id": UUID("33333333-3333-3333-3333-333333333333"),
        "rule_code": "IMPOSSIBLE_TRAVEL",
        "name": "Impossible Geo-Velocity",
        "rule_type": RuleTypeEnum.GEO_DISTANCE.value,
        "threshold_value": 800.0,
        "weight_points": 35,
        "is_active": True,
        "description": "Flags consecutive transactions with speed >800 km/h.",
    },
]


async def _ensure_seed_rules(db: AsyncSession):
    stmt = select(RiskRule)
    res = await db.execute(stmt)
    rules = res.scalars().all()
    if not rules:
        for seed in DEFAULT_SEED_RULES:
            rule_obj = RiskRule(**seed)
            db.add(rule_obj)
        await db.flush()


@router.get(
    "",
    response_model=List[RuleResponse],
    status_code=status.HTTP_200_OK,
    summary="List all risk rules",
    description="Returns all active and inactive fraud evaluation rules sorted with stable ordering."
)
async def list_rules(
    search: Optional[str] = Query(default=None, description="Search by code, name, or description"),
    rule_type: Optional[RuleTypeEnum] = Query(default=None, description="Filter by rule category"),
    is_active: Optional[bool] = Query(default=None, description="Filter by active status"),
    db: AsyncSession = Depends(get_db)
) -> List[RuleResponse]:
    await _ensure_seed_rules(db)
    stmt = select(RiskRule)

    if search and search.strip():
        pattern = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                RiskRule.rule_code.ilike(pattern),
                RiskRule.name.ilike(pattern),
                RiskRule.description.ilike(pattern)
            )
        )

    if rule_type:
        type_val = rule_type.value if hasattr(rule_type, "value") else str(rule_type)
        stmt = stmt.where(RiskRule.rule_type == type_val)

    if is_active is not None:
        stmt = stmt.where(RiskRule.is_active == is_active)

    stmt = stmt.order_by(RiskRule.created_at.desc(), RiskRule.id.desc())
    result = await db.execute(stmt)
    rules = result.scalars().all()
    return [RuleResponse.model_validate(rule) for rule in rules]


@router.get(
    "/{rule_id}",
    response_model=RuleResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Rule details found"},
        404: {"model": ErrorResponse, "description": "Rule not found"},
    },
    summary="Get risk rule detail",
    description="Retrieves a single risk rule by its unique ID."
)
async def get_rule_detail(
    rule_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> RuleResponse:
    await _ensure_seed_rules(db)
    stmt = select(RiskRule).where(RiskRule.id == rule_id)
    result = await db.execute(stmt)
    rule = result.scalar_one_or_none()

    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rule with ID {rule_id} not found"
        )

    return RuleResponse.model_validate(rule)



@router.post(
    "",
    response_model=RuleResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Rule created successfully"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
    summary="Create a new risk rule"
)
async def create_rule(
    payload: RuleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN", "ANALYST"))
) -> RuleResponse:
    # Check if rule code already exists
    stmt = select(RiskRule).where(RiskRule.rule_code == payload.rule_code)
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Rule with code '{payload.rule_code}' already exists."
        )

    rule = RiskRule(
        id=uuid4(),
        rule_code=payload.rule_code,
        name=payload.name,
        rule_type=payload.rule_type.value if hasattr(payload.rule_type, "value") else str(payload.rule_type),
        threshold_value=payload.threshold_value,
        weight_points=payload.weight_points,
        is_active=payload.is_active,
        description=payload.description
    )
    db.add(rule)
    await db.flush()
    return RuleResponse.model_validate(rule)


@router.patch(
    "/{rule_id}",
    response_model=RuleResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Rule updated successfully"},
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        404: {"model": ErrorResponse, "description": "Rule not found"},
    },
    summary="Update risk rule parameters"
)
async def update_rule(
    rule_id: UUID,
    payload: RuleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN", "ANALYST"))
) -> RuleResponse:
    stmt = select(RiskRule).where(RiskRule.id == rule_id)
    result = await db.execute(stmt)
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail=f"Rule with ID {rule_id} not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "rule_type" and hasattr(value, "value"):
            value = value.value
        setattr(rule, field, value)

    rule.updated_at = datetime.now(timezone.utc)
    await db.flush()
    return RuleResponse.model_validate(rule)


@router.delete(
    "/{rule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Rule deleted or deactivated successfully"},
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        404: {"model": ErrorResponse, "description": "Rule not found"},
    },
    summary="Delete or deactivate a risk rule",
    description="Deactivates or permanently removes a risk rule while ensuring evaluation audit safety."
)
async def delete_rule(
    rule_id: UUID,
    soft: bool = Query(default=True, description="Soft delete (deactivate) or hard delete rule"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN", "ANALYST"))
):
    await _ensure_seed_rules(db)
    stmt = select(RiskRule).where(RiskRule.id == rule_id)
    result = await db.execute(stmt)
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rule with ID {rule_id} not found"
        )

    if soft:
        rule.is_active = False
        rule.updated_at = datetime.now(timezone.utc)
    else:
        await db.delete(rule)

    await db.flush()
    return None


