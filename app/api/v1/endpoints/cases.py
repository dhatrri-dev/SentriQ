from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.case import InvestigationCase
from app.models.user import User
from app.models.transaction import Transaction
from app.schemas.case import CaseResolveRequest, CaseResponse
from app.schemas.common import CasePriorityEnum, CaseStatusEnum, ErrorResponse, PaginatedResponse, ResolutionActionEnum

router = APIRouter(prefix="/cases", tags=["Investigation Cases"])

DEFAULT_SEED_CASE = {
    "id": UUID("c1111111-1111-1111-1111-111111111111"),
    "transaction_id": UUID("99999999-9999-9999-9999-999999999999"),
    "user_id": UUID("88888888-8888-8888-8888-888888888888"),
    "risk_score": 65,
    "priority": CasePriorityEnum.HIGH.value,
    "status": CaseStatusEnum.PENDING.value,
    "resolution_notes": None,
    "resolved_at": None,
}


async def _ensure_seed_case(db: AsyncSession):
    stmt = select(InvestigationCase)
    res = await db.execute(stmt)
    cases = res.scalars().all()
    if not cases:
        # Ensure target user & transaction exist for foreign keys
        user_stmt = select(User).where(User.id == DEFAULT_SEED_CASE["user_id"])
        user = (await db.execute(user_stmt)).scalar_one_or_none()
        if not user:
            user = User(
                id=DEFAULT_SEED_CASE["user_id"],
                email="seed_user@example.com",
                full_name="Seed User",
                role="CLIENT"
            )
            db.add(user)
            await db.flush()

        tx_stmt = select(Transaction).where(Transaction.id == DEFAULT_SEED_CASE["transaction_id"])
        tx = (await db.execute(tx_stmt)).scalar_one_or_none()
        if not tx:
            tx = Transaction(
                id=DEFAULT_SEED_CASE["transaction_id"],
                user_id=DEFAULT_SEED_CASE["user_id"],
                card_hash="11112222333344445555666677778888",
                amount=1200.00,
                currency="USD",
                ip_address="198.51.100.1",
                latitude=40.7128,
                longitude=-74.0060,
                country="US",
                status="FLAGGED",
                risk_score=65,
                timestamp=datetime.now(timezone.utc)
            )
            db.add(tx)
            await db.flush()

        case_obj = InvestigationCase(**DEFAULT_SEED_CASE)
        db.add(case_obj)
        await db.flush()


@router.get(
    "",
    response_model=PaginatedResponse[CaseResponse],
    status_code=status.HTTP_200_OK,
    summary="List all investigation cases (Paginated)",
    description="Returns paginated list of all investigation cases sorted with stable ordering (newest first)."
)
async def list_cases(
    page: int = Query(default=1, ge=1, description="Page number"),
    size: int = Query(default=20, ge=1, le=100, description="Page size limit"),
    status_filter: Optional[CaseStatusEnum] = Query(default=None, alias="status", description="Filter by status"),
    priority_filter: Optional[CasePriorityEnum] = Query(default=None, alias="priority", description="Filter by priority"),
    db: AsyncSession = Depends(get_db)
) -> PaginatedResponse[CaseResponse]:
    await _ensure_seed_case(db)

    query = select(InvestigationCase)
    if status_filter:
        query = query.where(InvestigationCase.status == status_filter.value)
    if priority_filter:
        query = query.where(InvestigationCase.priority == priority_filter.value)

    # Stable ordering: newest created_at first, tie breaker on unique primary key id
    query = query.order_by(InvestigationCase.created_at.desc(), InvestigationCase.id.desc())

    # Count total matching
    count_query = select(func.count()).select_from(query.subquery())
    total_count = (await db.execute(count_query)).scalar() or 0

    # Paginate
    paginated_query = query.offset((page - 1) * size).limit(size)
    result = await db.execute(paginated_query)
    cases = result.scalars().all()

    items = [CaseResponse.model_validate(c) for c in cases]
    return PaginatedResponse[CaseResponse](
        total=total_count,
        page=page,
        size=size,
        items=items
    )


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
    priority: Optional[CasePriorityEnum] = Query(default=None),
    db: AsyncSession = Depends(get_db)
) -> PaginatedResponse[CaseResponse]:
    await _ensure_seed_case(db)
    
    query = select(InvestigationCase).where(InvestigationCase.status == CaseStatusEnum.PENDING.value)
    if priority:
        query = query.where(InvestigationCase.priority == priority.value)

    # Stable ordering: newest created_at first, tie breaker on unique primary key id
    query = query.order_by(InvestigationCase.created_at.desc(), InvestigationCase.id.desc())

    # Count total matching
    count_query = select(func.count()).select_from(query.subquery())
    total_count = (await db.execute(count_query)).scalar() or 0

    # Paginate
    paginated_query = query.offset((page - 1) * size).limit(size)
    result = await db.execute(paginated_query)
    cases = result.scalars().all()

    items = [CaseResponse.model_validate(c) for c in cases]
    return PaginatedResponse[CaseResponse](
        total=total_count,
        page=page,
        size=size,
        items=items
    )


@router.get(
    "/{case_id}",
    response_model=CaseResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Case details found"},
        404: {"model": ErrorResponse, "description": "Case not found"},
    },
    summary="Get investigation case detail",
    description="Retrieves single investigation case record by its unique ID."
)
async def get_case_detail(
    case_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> CaseResponse:
    await _ensure_seed_case(db)
    stmt = select(InvestigationCase).where(InvestigationCase.id == case_id)
    result = await db.execute(stmt)
    case = result.scalar_one_or_none()

    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case with ID {case_id} not found"
        )

    return CaseResponse.model_validate(case)


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
    payload: CaseResolveRequest,
    db: AsyncSession = Depends(get_db)
) -> CaseResponse:
    stmt = select(InvestigationCase).where(InvestigationCase.id == case_id)
    result = await db.execute(stmt)
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case with ID {case_id} not found"
        )

    new_status = (
        CaseStatusEnum.RESOLVED_APPROVED.value
        if payload.action == ResolutionActionEnum.APPROVE
        else CaseStatusEnum.RESOLVED_BLOCKED.value
    )
    case.status = new_status
    case.resolution_notes = payload.resolution_notes
    case.assigned_analyst_id = uuid4()
    case.resolved_at = datetime.now(timezone.utc)

    await db.flush()
    return CaseResponse.model_validate(case)


