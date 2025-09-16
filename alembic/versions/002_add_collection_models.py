"""Add collection models for contract notes, customers, loans and data integrity alerts

Revision ID: 002_add_collection_models
Revises: 
Create Date: 2025-01-22 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002_add_collection_models'
down_revision = None
depends_on = None


def upgrade() -> None:
    # Create contract_notes table
    op.create_table('contract_notes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('filename', sa.String(length=500), nullable=False),
        sa.Column('file_path', sa.String(length=500), nullable=False),
        sa.Column('extracted_data', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('contract_emi_amount', sa.Float(), nullable=True),
        sa.Column('contract_due_day', sa.Integer(), nullable=True),
        sa.Column('contract_late_fee_percent', sa.Float(), nullable=True),
        sa.Column('contract_default_clause', sa.String(length=2000), nullable=True),
        sa.Column('contract_governing_law', sa.String(length=500), nullable=True),
        sa.Column('contract_interest_rate', sa.Float(), nullable=True),
        sa.Column('contract_loan_amount', sa.Float(), nullable=True),
        sa.Column('contract_tenure_months', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_contract_notes_id'), 'contract_notes', ['id'], unique=False)

    # Create customers table
    op.create_table('customers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('customer_no', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=500), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('phone', sa.String(length=50), nullable=True),
        sa.Column('address', sa.String(length=1000), nullable=True),
        sa.Column('contract_note_id', sa.Integer(), nullable=True),
        sa.Column('cbs_emi_amount', sa.Float(), nullable=True),
        sa.Column('cbs_due_day', sa.Integer(), nullable=True),
        sa.Column('cbs_last_payment_date', sa.Date(), nullable=True),
        sa.Column('cbs_outstanding_amount', sa.Float(), nullable=True),
        sa.Column('cbs_risk_level', sa.String(length=20), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['contract_note_id'], ['contract_notes.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('customer_no')
    )
    op.create_index(op.f('ix_customers_id'), 'customers', ['id'], unique=False)
    op.create_index(op.f('ix_customers_customer_no'), 'customers', ['customer_no'], unique=False)

    # Create loans table
    op.create_table('loans',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('loan_id', sa.String(length=100), nullable=False),
        sa.Column('customer_id', sa.Integer(), nullable=False),
        sa.Column('loan_amount', sa.Float(), nullable=True),
        sa.Column('emi_amount', sa.Float(), nullable=True),
        sa.Column('tenure_months', sa.Integer(), nullable=True),
        sa.Column('interest_rate', sa.Float(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('outstanding_amount', sa.Float(), nullable=True),
        sa.Column('last_payment_date', sa.Date(), nullable=True),
        sa.Column('next_due_date', sa.Date(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('loan_id')
    )
    op.create_index(op.f('ix_loans_id'), 'loans', ['id'], unique=False)
    op.create_index(op.f('ix_loans_loan_id'), 'loans', ['loan_id'], unique=False)

    # Create data_integrity_alerts table
    op.create_table('data_integrity_alerts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('alert_type', sa.String(length=100), nullable=False),
        sa.Column('customer_id', sa.Integer(), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('description', sa.String(length=2000), nullable=True),
        sa.Column('cbs_value', sa.String(length=500), nullable=True),
        sa.Column('contract_value', sa.String(length=500), nullable=True),
        sa.Column('is_resolved', sa.Boolean(), nullable=True),
        sa.Column('resolved_by', sa.Integer(), nullable=True),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_data_integrity_alerts_id'), 'data_integrity_alerts', ['id'], unique=False)

    # Create automation_rules table
    op.create_table('automation_rules',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('conditions', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('actions', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_automation_rules_id'), 'automation_rules', ['id'], unique=False)


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_index(op.f('ix_automation_rules_id'), table_name='automation_rules')
    op.drop_table('automation_rules')
    
    op.drop_index(op.f('ix_data_integrity_alerts_id'), table_name='data_integrity_alerts')
    op.drop_table('data_integrity_alerts')
    
    op.drop_index(op.f('ix_loans_loan_id'), table_name='loans')
    op.drop_index(op.f('ix_loans_id'), table_name='loans')
    op.drop_table('loans')
    
    op.drop_index(op.f('ix_customers_customer_no'), table_name='customers')
    op.drop_index(op.f('ix_customers_id'), table_name='customers')
    op.drop_table('customers')
    
    op.drop_index(op.f('ix_contract_notes_id'), table_name='contract_notes')
    op.drop_table('contract_notes')
