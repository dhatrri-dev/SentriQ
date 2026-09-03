"""Initial schema migration

Revision ID: 001
Revises: 
Create Date: 2026-09-03

Creates all core tables:
- users
- transactions  
- risk_rules
- evaluation_logs
- evaluation_log_items
- investigation_cases
- blocklist_entities
"""

from typing import Sequence, Union
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op


revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Users table
    op.create_table(
        'users',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=True),
        sa.Column('role', sa.String(length=50), nullable=False, server_default='CLIENT'),
        sa.Column('avg_monthly_spend', sa.Numeric(12, 2), nullable=False, server_default='0.00'),
        sa.Column('total_transaction_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_users_id', 'users', ['id'])
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

    # Transactions table
    op.create_table(
        'transactions',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('card_hash', sa.String(length=64), nullable=False),
        sa.Column('card_bin', sa.String(length=8), nullable=True),
        sa.Column('amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False, server_default='USD'),
        sa.Column('ip_address', sa.String(length=45), nullable=False),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('country', sa.String(length=3), nullable=False),
        sa.Column('city', sa.String(length=100), nullable=True),
        sa.Column('device_id', sa.String(length=100), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='PENDING'),
        sa.Column('risk_score', sa.Integer(), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_transactions_id', 'transactions', ['id'])
    op.create_index('ix_transactions_user_id', 'transactions', ['user_id'])
    op.create_index('ix_transactions_card_hash', 'transactions', ['card_hash'])
    op.create_index('ix_transactions_user_timestamp', 'transactions', ['user_id', 'timestamp'])
    op.create_index('ix_transactions_card_timestamp', 'transactions', ['card_hash', 'timestamp'])

    # Risk Rules table
    op.create_table(
        'risk_rules',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('rule_code', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('rule_type', sa.String(length=50), nullable=False),
        sa.Column('threshold_value', sa.Float(), nullable=False),
        sa.Column('weight_points', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('rule_code'),
    )
    op.create_index('ix_risk_rules_id', 'risk_rules', ['id'])
    op.create_index('ix_risk_rules_rule_code', 'risk_rules', ['rule_code'], unique=True)
    op.create_index('ix_risk_rules_is_active', 'risk_rules', ['is_active'])

    # Evaluation Logs table
    op.create_table(
        'evaluation_logs',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('transaction_id', sa.Uuid(), nullable=False),
        sa.Column('final_score', sa.Integer(), nullable=False),
        sa.Column('decision', sa.String(length=50), nullable=False),
        sa.Column('rules_triggered_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('execution_time_ms', sa.Float(), nullable=False),
        sa.Column('evaluated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['transaction_id'], ['transactions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('transaction_id'),
    )
    op.create_index('ix_evaluation_logs_id', 'evaluation_logs', ['id'])
    op.create_index('ix_evaluation_logs_decision', 'evaluation_logs', ['decision'])
    op.create_index('ix_evaluation_logs_final_score', 'evaluation_logs', ['final_score'])

    # Evaluation Log Items table
    op.create_table(
        'evaluation_log_items',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('evaluation_log_id', sa.Uuid(), nullable=False),
        sa.Column('rule_id', sa.Uuid(), nullable=True),
        sa.Column('rule_code', sa.String(length=50), nullable=False),
        sa.Column('points_assigned', sa.Integer(), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['evaluation_log_id'], ['evaluation_logs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['rule_id'], ['risk_rules.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_evaluation_log_items_id', 'evaluation_log_items', ['id'])
    op.create_index('ix_evaluation_log_items_evaluation_log_id', 'evaluation_log_items', ['evaluation_log_id'])

    # Investigation Cases table
    op.create_table(
        'investigation_cases',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('transaction_id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('assigned_analyst_id', sa.Uuid(), nullable=True),
        sa.Column('risk_score', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='PENDING'),
        sa.Column('priority', sa.String(length=50), nullable=False, server_default='MEDIUM'),
        sa.Column('resolution_notes', sa.Text(), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['assigned_analyst_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['transaction_id'], ['transactions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('transaction_id'),
    )
    op.create_index('ix_investigation_cases_id', 'investigation_cases', ['id'])
    op.create_index('ix_investigation_cases_status', 'investigation_cases', ['status'])
    op.create_index('ix_investigation_cases_priority', 'investigation_cases', ['priority'])

    # Blocklist Entities table
    op.create_table(
        'blocklist_entities',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('entity_type', sa.String(length=50), nullable=False),
        sa.Column('entity_value', sa.String(length=255), nullable=False),
        sa.Column('reason', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_blocklist_entities_id', 'blocklist_entities', ['id'])
    op.create_index('ix_blocklist_entities_entity_type', 'blocklist_entities', ['entity_type'])
    op.create_index('ix_blocklist_entities_is_active', 'blocklist_entities', ['is_active'])
    op.create_index('ix_blocklist_type_value', 'blocklist_entities', ['entity_type', 'entity_value'])


def downgrade() -> None:
    op.drop_table('blocklist_entities')
    op.drop_table('investigation_cases')
    op.drop_table('evaluation_log_items')
    op.drop_table('evaluation_logs')
    op.drop_table('risk_rules')
    op.drop_table('transactions')
    op.drop_table('users')
