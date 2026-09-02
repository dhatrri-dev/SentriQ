from enum import Enum
from typing import Generic, List, Optional, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class DecisionEnum(str, Enum):
    ALLOW = "ALLOW"
    FLAG_FOR_REVIEW = "FLAG_FOR_REVIEW"
    BLOCK = "BLOCK"


class RuleTypeEnum(str, Enum):
    VELOCITY = "VELOCITY"
    AMOUNT_ANOMALY = "AMOUNT_ANOMALY"
    GEO_DISTANCE = "GEO_DISTANCE"
    BLOCKLIST = "BLOCKLIST"
    CUSTOM = "CUSTOM"


class CaseStatusEnum(str, Enum):
    PENDING = "PENDING"
    IN_REVIEW = "IN_REVIEW"
    RESOLVED_APPROVED = "RESOLVED_APPROVED"
    RESOLVED_BLOCKED = "RESOLVED_BLOCKED"


class CasePriorityEnum(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ResolutionActionEnum(str, Enum):
    APPROVE = "APPROVE"
    BLOCK = "BLOCK"


class EntityTypeEnum(str, Enum):
    IP = "IP"
    CARD_BIN = "CARD_BIN"
    CARD_HASH = "CARD_HASH"
    EMAIL_DOMAIN = "EMAIL_DOMAIN"
    COUNTRY = "COUNTRY"


class ErrorDetail(BaseModel):
    loc: Optional[List[str]] = Field(default=None, description="Location of the error in request")
    msg: str = Field(description="Error message")
    type: str = Field(description="Error type identifier")


class ErrorResponse(BaseModel):
    error: str = Field(description="Error summary")
    detail: Optional[str] = Field(default=None, description="Detailed explanation")
    errors: Optional[List[ErrorDetail]] = Field(default=None, description="Validation field errors")


class PaginatedResponse(BaseModel, Generic[T]):
    total: int = Field(description="Total number of items")
    page: int = Field(default=1, description="Current page number")
    size: int = Field(default=20, description="Page size limit")
    items: List[T] = Field(description="List of paginated items")
