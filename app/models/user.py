from datetime import datetime, timezone
import uuid
from sqlalchemy import DateTime, Integer, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4, index=True
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(String(50), default="CLIENT", nullable=False)
    avg_monthly_spend: Mapped[float] = mapped_column(Numeric(12, 2), default=0.00, nullable=False)
    total_transaction_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    transactions = relationship("Transaction", back_populates="user", cascade="all, delete-orphan")
    cases = relationship("InvestigationCase", back_populates="user", foreign_keys="InvestigationCase.user_id")
