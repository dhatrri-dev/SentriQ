from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4
from fastapi import APIRouter, HTTPException, Query, status
from app.schemas.case import CaseResolveRequest, CaseResponse
from app.schemas.common import CasePriorityEnum, CaseStatusEnum, ErrorResponse, PaginatedResponse, ResolutionActionEnum

router = APIRouter(prefix="/cases", tags=["Investigation Cases"])

MOCK_CASES = [
    {
        "id": UUID("c1111111-1111-1111-1111-111111111111"),
        "transaction_id": UUID("99999999-9999-9999-9999-999999999999"),
        "user_id": UUID("88888888-8888-8888-8888-888888888888"),
        "risk_score": 65,
        "priority": CasePriorityEnum.HIGH,
        "status": CaseStatusEnum.PENDING,
        "assigned_analyst_id": None,
        "resolution_notes": None,
        "resolved_at": None,
        "created_at": datetime.now(timezone.utc),
    }
]


@router.get(
    "/pending",
    response_model=PaginatedResponse[CaseResponse],
    status_code=status.HTTP_200_OK,
    summary="List pending investigation cases",
    description="Returns paginated list of transactions flagged for analyst manual review."
)
async def list_pending_cases(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    priority: Optional[CasePriorityEnum] = Query(default=None)
) -> PaginatedResponse[CaseResponse]:
    filtered = [
        CaseResponse(**c) for c in MOCK_CASES 
        if c["status"] == CaseStatusEnum.PENDING and (priority is None or c["priority"] == priority)
    ]
    return PaginatedResponse[CaseResponse](
        total=len(filtered),
        page=page,
        size=size,
        items=filtered
    )


@router.post(
    "/{case_id}/resolve",
    response_model=CaseResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Case successfully resolved"},
        404: {"model": ErrorResponse, "description": "Case not found"},
    },
    summary="Resolve an investigation case",
    description="Approves or blocks a flagged transaction with mandatory analyst review notes."
)
async def resolve_case(
    case_id: UUID,
    payload: CaseResolveRequest
) -> CaseResponse:
    for case in MOCK_CASES:
        if case["id"] == case_id:
            new_status = (
                CaseStatusEnum.RESOLVED_APPROVED 
                if payload.action == ResolutionActionEnum.APPROVE 
                else CaseStatusEnum.RESOLVED_BLOCKED
            )
            case["status"] = new_status
            case["resolution_notes"] = payload.resolution_notes
            case["assigned_analyst_id"] = uuid4()
            case["resolved_at"] = datetime.now(timezone.utc)
            return CaseResponse(**case)
    raise HTTPException(status_code=404, detail=f"Case with ID {case_id} not found")
