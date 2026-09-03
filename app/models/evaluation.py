from datetime import datetime, timezone
import uuid
from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class EvaluationLog(Base):
    __tablename__ = "evaluation_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4, index=True
    )
    transaction_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("transactions.id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )
    final_score: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    decision: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    rules_triggered_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    execution_time_ms: Mapped[float] = mapped_column(Float, nullable=False)

    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True
    )

    # Relationships
    transaction = relationship("Transaction", back_populates="evaluation_log")
    items = relationship("EvaluationLogItem", back_populates="evaluation_log", cascade="all, delete-orphan")


class EvaluationLogItem(Base):
    __tablename__ = "evaluation_log_items"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4, index=True
    )
    evaluation_log_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("evaluation_logs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    rule_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("risk_rules.id", ondelete="SET NULL"), nullable=True
    )
    rule_code: Mapped[str] = mapped_column(String(50), nullable=False)
    points_assigned: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[dict] = mapped_column(JSON, nullable=True)

    # Relationships
    evaluation_log = relationship("EvaluationLog", back_populates="items")
    rule = relationship("RiskRule", back_populates="log_items")
