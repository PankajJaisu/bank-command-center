"""Add policy rule fields to automation_rules

Revision ID: 004_add_policy_rule_fields
Revises: 003_add_customer_fields
Create Date: 2025-08-20 14:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '004_add_policy_rule_fields'
down_revision = '003_add_customer_fields'
branch_labels = None
depends_on = None


def upgrade():
    # Add new columns to automation_rules table
    op.add_column('automation_rules', sa.Column('rule_level', sa.String(), nullable=True))
    op.add_column('automation_rules', sa.Column('segment', sa.String(), nullable=True))
    op.add_column('automation_rules', sa.Column('customer_id', sa.String(), nullable=True))
    op.add_column('automation_rules', sa.Column('source_document', sa.String(), nullable=True))
    op.add_column('automation_rules', sa.Column('status', sa.String(), nullable=True, default='active'))


def downgrade():
    # Remove the columns
    op.drop_column('automation_rules', 'status')
    op.drop_column('automation_rules', 'source_document')
    op.drop_column('automation_rules', 'customer_id')
    op.drop_column('automation_rules', 'segment')
    op.drop_column('automation_rules', 'rule_level')
