from datetime import datetime, timezone
import uuid
from sqlalchemy import Boolean, DateTime, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class BlocklistEntity(Base):
    __tablename__ = "blocklist_entities"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4, index=True
    )
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    entity_value: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    __table_args__ = (
        Index("ix_blocklist_type_value", "entity_type", "entity_value"),
    )
