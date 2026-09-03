import uuid
from datetime import datetime, timezone
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from tests.db_fixtures import db_session, setup_test_database  # noqa: F401
from app.models.user import User
from app.models.rule import RiskRule
from app.models.transaction import Transaction
from app.models.evaluation import EvaluationLog


@pytest.mark.asyncio
async def test_database_tables_created(db_session: AsyncSession):
    """Verify all core ORM tables exist in the test database."""
    result = await db_session.execute(
        text("SELECT name FROM sqlite_master WHERE type='table'")
    )
    tables = {row[0] for row in result.fetchall()}

    assert "users" in tables
    assert "transactions" in tables
    assert "risk_rules" in tables
    assert "evaluation_logs" in tables
    assert "evaluation_log_items" in tables
    assert "investigation_cases" in tables
    assert "blocklist_entities" in tables


@pytest.mark.asyncio
async def test_create_and_read_user_model(db_session: AsyncSession):
    """Verify User model writes and reads correctly from the database."""
    user = User(
        id=uuid.uuid4(),
        email=f"test_{uuid.uuid4().hex[:8]}@sentriq.com",
        full_name="Test User",
        role="CLIENT",
        avg_monthly_spend=500.00,
        total_transaction_count=0,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(user)
    await db_session.flush()

    from sqlalchemy import select
    result = await db_session.execute(select(User).where(User.id == user.id))
    fetched = result.scalar_one_or_none()
    assert fetched is not None
    assert fetched.email == user.email
    assert fetched.role == "CLIENT"


@pytest.mark.asyncio
async def test_create_and_read_risk_rule_model(db_session: AsyncSession):
    """Verify RiskRule model writes and reads correctly from the database."""
    rule = RiskRule(
        id=uuid.uuid4(),
        rule_code=f"TEST_RULE_{uuid.uuid4().hex[:6].upper()}",
        name="Test Velocity Rule",
        rule_type="VELOCITY",
        threshold_value=3.0,
        weight_points=40,
        is_active=True,
        description="Test rule for unit testing",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(rule)
    await db_session.flush()

    from sqlalchemy import select
    result = await db_session.execute(select(RiskRule).where(RiskRule.id == rule.id))
    fetched = result.scalar_one_or_none()
    assert fetched is not None
    assert fetched.rule_type == "VELOCITY"
    assert fetched.weight_points == 40
    assert fetched.is_active is True


@pytest.mark.asyncio
async def test_async_session_is_configured(db_session: AsyncSession):
    """Verify async database session is properly configured."""
    assert db_session is not None
    result = await db_session.execute(text("SELECT 1"))
    val = result.scalar()
    assert val == 1
