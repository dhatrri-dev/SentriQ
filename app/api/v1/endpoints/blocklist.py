from datetime import datetime, timezone
from typing import List
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.blocklist import BlocklistEntity
from app.schemas.blocklist import BlocklistCreate, BlocklistResponse
from app.schemas.common import EntityTypeEnum, ErrorResponse

router = APIRouter(prefix="/blocklist", tags=["Blocklist Management"])

DEFAULT_SEED_BLOCKLIST = [
    {
        "id": UUID("44444444-4444-4444-4444-444444444444"),
        "entity_type": EntityTypeEnum.EMAIL_DOMAIN.value,
        "entity_value": "tempmail.com",
        "reason": "Disposable email provider used in card testing attacks.",
        "is_active": True,
    }
]


async def _ensure_seed_blocklist(db: AsyncSession):
    stmt = select(BlocklistEntity)
    res = await db.execute(stmt)
    items = res.scalars().all()
    if not items:
        for seed in DEFAULT_SEED_BLOCKLIST:
            entity = BlocklistEntity(**seed)
            db.add(entity)
        await db.flush()


@router.get(
    "",
    response_model=List[BlocklistResponse],
    status_code=status.HTTP_200_OK,
    summary="List blocklist entries",
    description="Returns all active blocklist entries sorted with stable ordering."
)
async def list_blocklist(db: AsyncSession = Depends(get_db)) -> List[BlocklistResponse]:
    await _ensure_seed_blocklist(db)
    stmt = select(BlocklistEntity).where(BlocklistEntity.is_active == True).order_by(BlocklistEntity.created_at.desc(), BlocklistEntity.id.desc())
    result = await db.execute(stmt)
    items = result.scalars().all()
    return [BlocklistResponse.model_validate(item) for item in items]


@router.get(
    "/{entry_id}",
    response_model=BlocklistResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Blocklist entry details found"},
        404: {"model": ErrorResponse, "description": "Entry not found"},
    },
    summary="Get blocklist entry detail",
    description="Retrieves a single blocklist entry by its unique ID."
)
async def get_blocklist_detail(
    entry_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> BlocklistResponse:
    await _ensure_seed_blocklist(db)
    stmt = select(BlocklistEntity).where(BlocklistEntity.id == entry_id)
    result = await db.execute(stmt)
    entry = result.scalar_one_or_none()

    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Blocklist entry with ID {entry_id} not found"
        )

    return BlocklistResponse.model_validate(entry)



@router.post(
    "",
    response_model=BlocklistResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add entity to blocklist"
)
async def add_to_blocklist(
    payload: BlocklistCreate,
    db: AsyncSession = Depends(get_db)
) -> BlocklistResponse:
    entity_type_str = payload.entity_type.value if hasattr(payload.entity_type, "value") else str(payload.entity_type)
    entry = BlocklistEntity(
        id=uuid4(),
        entity_type=entity_type_str,
        entity_value=payload.entity_value,
        reason=payload.reason,
        expires_at=payload.expires_at,
        is_active=True
    )
    db.add(entry)
    await db.flush()
    return BlocklistResponse.model_validate(entry)


@router.delete(
    "/{entry_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Entity removed from blocklist"},
        404: {"model": ErrorResponse, "description": "Entry not found"},
    },
    summary="Remove entity from blocklist"
)
async def remove_from_blocklist(
    entry_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(BlocklistEntity).where(BlocklistEntity.id == entry_id)
    result = await db.execute(stmt)
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail=f"Blocklist entry {entry_id} not found")

    entry.is_active = False
    await db.flush()
    return None

