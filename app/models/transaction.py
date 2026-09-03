from datetime import datetime, timezone
import uuid
from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    card_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    card_bin: Mapped[str] = mapped_column(String(8), nullable=True, index=True)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    ip_address: Mapped[str] = mapped_column(String(45), nullable=False, index=True)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    country: Mapped[str] = mapped_column(String(3), nullable=False, index=True)
    city: Mapped[str] = mapped_column(String(100), nullable=True)
    device_id: Mapped[str] = mapped_column(String(100), nullable=True, index=True)

    status: Mapped[str] = mapped_column(String(50), default="PENDING", nullable=False, index=True)
    risk_score: Mapped[int] = mapped_column(Integer, nullable=True)

    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    user = relationship("User", back_populates="transactions")
    evaluation_log = relationship("EvaluationLog", back_populates="transaction", uselist=False, cascade="all, delete-orphan")
    case = relationship("InvestigationCase", back_populates="transaction", uselist=False, cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_transactions_user_timestamp", "user_id", "timestamp"),
        Index("ix_transactions_card_timestamp", "card_hash", "timestamp"),
    )
