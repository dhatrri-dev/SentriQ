import pytest
from uuid import UUID, uuid4
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from tests.db_fixtures import setup_test_database, db_session  # noqa: F401
from app.models.transaction import Transaction
from app.models.evaluation import EvaluationLog, EvaluationLogItem
from app.models.case import InvestigationCase
from app.models.rule import RiskRule
from app.models.blocklist import BlocklistEntity


@pytest.mark.asyncio
async def test_create_transaction_evaluate_persists_to_db(async_client: AsyncClient, db_session: AsyncSession):
    user_id = uuid4()
    payload = {
        "user_id": str(user_id),
        "card_hash": "a1b2c3d4e5f67890abcdef1234567890abcdef12",
        "card_bin": "411111",
        "amount": 7500.00,  # Triggers AMOUNT_SPIKE_5X rule -> FLAGGED / BLOCKED
        "currency": "USD",
        "ip_address": "198.51.100.55",
        "location": {
            "latitude": 37.7749,
            "longitude": -122.4194,
            "country": "US",
            "city": "San Francisco"
        },
        "device_id": "device_sf_001",
        "timestamp": "2026-09-04T12:00:00Z"
    }

    response = await async_client.post("/api/v1/transactions/evaluate", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["decision"] in ("FLAG_FOR_REVIEW", "BLOCK")
    assert data["risk_score"] >= 65
    assert data["case_id"] is not None
    tx_id = UUID(data["transaction_id"])


    # Verify Database Persistence
    tx_stmt = select(Transaction).where(Transaction.id == tx_id)
    tx = (await db_session.execute(tx_stmt)).scalar_one_or_none()
    assert tx is not None
    assert tx.user_id == user_id
    assert tx.amount == 7500.00
    assert tx.status == data["decision"]

    # Verify EvaluationLog Persistence
    log_stmt = select(EvaluationLog).where(EvaluationLog.transaction_id == tx_id)
    log = (await db_session.execute(log_stmt)).scalar_one_or_none()
    assert log is not None
    assert log.final_score == data["risk_score"]
    assert log.decision == data["decision"]


    # Verify EvaluationLogItem Persistence
    item_stmt = select(EvaluationLogItem).where(EvaluationLogItem.evaluation_log_id == log.id)
    items = (await db_session.execute(item_stmt)).scalars().all()
    assert len(items) >= 1
    assert items[0].rule_code == "AMOUNT_SPIKE_5X"

    # Verify InvestigationCase Persistence
    case_stmt = select(InvestigationCase).where(InvestigationCase.transaction_id == tx_id)
    case = (await db_session.execute(case_stmt)).scalar_one_or_none()
    assert case is not None
    assert case.priority == ("HIGH" if data["decision"] == "BLOCK" else "MEDIUM")
    assert case.status == "PENDING"




@pytest.mark.asyncio
async def test_create_transaction_evaluate_validation_errors(async_client: AsyncClient):
    invalid_payload = {
        "user_id": "not-a-uuid",
        "card_hash": "short",
        "amount": -200.00,  # invalid negative amount
        "currency": "INVALID",
        "ip_address": "999.999.999.999",  # invalid IP
        "location": {
            "latitude": 180.0,  # > 90 invalid latitude
            "longitude": -74.0060,
            "country": "U"
        }
    }
    response = await async_client.post("/api/v1/transactions/evaluate", json=invalid_payload)
    assert response.status_code == 422
    data = response.json()
    assert "error" in data or "detail" in data


@pytest.mark.asyncio
async def test_create_rule_persists_to_db(async_client: AsyncClient, db_session: AsyncSession):
    rule_code = f"TEST_RULE_{uuid4().hex[:6].upper()}"
    payload = {
        "rule_code": rule_code,
        "name": "Integration Test Rule",
        "rule_type": "CUSTOM",
        "threshold_value": 1500.0,
        "weight_points": 30,
        "is_active": True,
        "description": "Rule created during integration testing"
    }

    response = await async_client.post("/api/v1/rules", json=payload)
    assert response.status_code == 201
    created_rule = response.json()
    assert created_rule["rule_code"] == rule_code

    # Verify DB
    stmt = select(RiskRule).where(RiskRule.rule_code == rule_code)
    rule_in_db = (await db_session.execute(stmt)).scalar_one_or_none()
    assert rule_in_db is not None
    assert rule_in_db.weight_points == 30


@pytest.mark.asyncio
async def test_add_blocklist_persists_to_db(async_client: AsyncClient, db_session: AsyncSession):
    ip_val = "203.0.113.199"
    payload = {
        "entity_type": "IP",
        "entity_value": ip_val,
        "reason": "Known fraud botnet IP range"
    }

    response = await async_client.post("/api/v1/blocklist", json=payload)
    assert response.status_code == 201
    entry = response.json()
    assert entry["entity_value"] == ip_val

    # Verify DB
    stmt = select(BlocklistEntity).where(BlocklistEntity.entity_value == ip_val)
    block_in_db = (await db_session.execute(stmt)).scalar_one_or_none()
    assert block_in_db is not None
    assert block_in_db.is_active is True


@pytest.mark.asyncio
async def test_resolve_case_persists_to_db(async_client: AsyncClient, db_session: AsyncSession):
    # First get pending case
    get_res = await async_client.get("/api/v1/cases/pending")
    assert get_res.status_code == 200
    cases = get_res.json()["items"]
    assert len(cases) > 0
    target_case_id = UUID(cases[0]["id"])

    resolve_payload = {
        "action": "APPROVE",
        "resolution_notes": "Verified customer identity and transaction source."
    }

    response = await async_client.post(f"/api/v1/cases/{target_case_id}/resolve", json=resolve_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "RESOLVED_APPROVED"
    assert data["resolution_notes"] == "Verified customer identity and transaction source."

    # Verify DB state
    stmt = select(InvestigationCase).where(InvestigationCase.id == target_case_id)
    case_in_db = (await db_session.execute(stmt)).scalar_one_or_none()
    assert case_in_db is not None
    assert case_in_db.status == "RESOLVED_APPROVED"

