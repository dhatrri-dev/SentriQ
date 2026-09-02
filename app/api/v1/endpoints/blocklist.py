from datetime import datetime, timezone
from typing import List
from uuid import UUID, uuid4
from fastapi import APIRouter, HTTPException, status
from app.schemas.blocklist import BlocklistCreate, BlocklistResponse
from app.schemas.common import EntityTypeEnum, ErrorResponse

router = APIRouter(prefix="/blocklist", tags=["Blocklist Management"])

MOCK_BLOCKLIST = [
    {
        "id": UUID("44444444-4444-4444-4444-444444444444"),
        "entity_type": EntityTypeEnum.EMAIL_DOMAIN,
        "entity_value": "tempmail.com",
        "reason": "Disposable email provider used in card testing attacks.",
        "is_active": True,
        "expires_at": None,
        "created_at": datetime.now(timezone.utc),
    }
]


@router.get(
    "",
    response_model=List[BlocklistResponse],
    status_code=status.HTTP_200_OK,
    summary="List blocklist entries"
)
async def list_blocklist() -> List[BlocklistResponse]:
    return [BlocklistResponse(**item) for item in MOCK_BLOCKLIST if item["is_active"]]


@router.post(
    "",
    response_model=BlocklistResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add entity to blocklist"
)
async def add_to_blocklist(payload: BlocklistCreate) -> BlocklistResponse:
    entry = {
        "id": uuid4(),
        **payload.model_dump(),
        "is_active": True,
        "created_at": datetime.now(timezone.utc)
    }
    MOCK_BLOCKLIST.append(entry)
    return BlocklistResponse(**entry)


@router.delete(
    "/{entry_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Entity removed from blocklist"},
        404: {"model": ErrorResponse, "description": "Entry not found"},
    },
    summary="Remove entity from blocklist"
)
async def remove_from_blocklist(entry_id: UUID):
    for entry in MOCK_BLOCKLIST:
        if entry["id"] == entry_id:
            entry["is_active"] = False
            return None
    raise HTTPException(status_code=404, detail=f"Blocklist entry {entry_id} not found")
