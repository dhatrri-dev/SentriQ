from datetime import datetime, timezone
from typing import List
from uuid import UUID, uuid4
from fastapi import APIRouter, HTTPException, status
from app.schemas.rule import RuleCreate, RuleResponse, RuleUpdate
from app.schemas.common import ErrorResponse, RuleTypeEnum

router = APIRouter(prefix="/rules", tags=["Risk Rules"])

# In-memory mock list for API design verification
MOCK_RULES = [
    {
        "id": UUID("11111111-1111-1111-1111-111111111111"),
        "rule_code": "VELOCITY_60S",
        "name": "Rapid Transaction Velocity",
        "rule_type": RuleTypeEnum.VELOCITY,
        "threshold_value": 3.0,
        "weight_points": 40,
        "is_active": True,
        "description": "Flags >3 transactions on same card in 60s window.",
        "created_at": datetime.now(timezone.utc),
        "updated_at": None,
    },
    {
        "id": UUID("22222222-2222-2222-2222-222222222222"),
        "rule_code": "AMOUNT_SPIKE_5X",
        "name": "Amount Spike Anomaly",
        "rule_type": RuleTypeEnum.AMOUNT_ANOMALY,
        "threshold_value": 5.0,
        "weight_points": 50,
        "is_active": True,
        "description": "Flags transactions >5x historical average spend.",
        "created_at": datetime.now(timezone.utc),
        "updated_at": None,
    },
    {
        "id": UUID("33333333-3333-3333-3333-333333333333"),
        "rule_code": "IMPOSSIBLE_TRAVEL",
        "name": "Impossible Geo-Velocity",
        "rule_type": RuleTypeEnum.GEO_DISTANCE,
        "threshold_value": 800.0,
        "weight_points": 35,
        "is_active": True,
        "description": "Flags consecutive transactions with speed >800 km/h.",
        "created_at": datetime.now(timezone.utc),
        "updated_at": None,
    },
]


@router.get(
    "",
    response_model=List[RuleResponse],
    status_code=status.HTTP_200_OK,
    summary="List all risk rules",
    description="Returns all active and inactive fraud evaluation rules."
)
async def list_rules() -> List[RuleResponse]:
    return [RuleResponse(**rule) for rule in MOCK_RULES]


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
async def create_rule(payload: RuleCreate) -> RuleResponse:
    new_rule = {
        "id": uuid4(),
        **payload.model_dump(),
        "created_at": datetime.now(timezone.utc),
        "updated_at": None
    }
    MOCK_RULES.append(new_rule)
    return RuleResponse(**new_rule)


@router.patch(
    "/{rule_id}",
    response_model=RuleResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Rule updated successfully"},
        404: {"model": ErrorResponse, "description": "Rule not found"},
    },
    summary="Update risk rule parameters"
)
async def update_rule(rule_id: UUID, payload: RuleUpdate) -> RuleResponse:
    for rule in MOCK_RULES:
        if rule["id"] == rule_id:
            update_data = payload.model_dump(exclude_unset=True)
            rule.update(update_data)
            rule["updated_at"] = datetime.now(timezone.utc)
            return RuleResponse(**rule)
    raise HTTPException(status_code=404, detail=f"Rule with ID {rule_id} not found")
