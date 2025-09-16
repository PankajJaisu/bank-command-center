"""Add CIBIL score and additional customer fields

Revision ID: 003_add_customer_fields
Revises: 002_add_collection_models
Create Date: 2025-01-16 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = '003_add_customer_fields'
down_revision = '002_add_collection_models'
branch_labels = None
depends_on = None


def upgrade():
    """Add new customer fields from spreadsheet data format"""
    
    # Add new columns to customers table
    op.add_column('customers', sa.Column('cibil_score', sa.Integer(), nullable=True))
    op.add_column('customers', sa.Column('days_since_employment', sa.Integer(), nullable=True))
    op.add_column('customers', sa.Column('employment_status', sa.String(length=50), nullable=True))
    op.add_column('customers', sa.Column('cbs_income_verification', sa.String(length=50), nullable=True))
    op.add_column('customers', sa.Column('salary_last_date', sa.Date(), nullable=True))
    op.add_column('customers', sa.Column('pending_amount', sa.Float(), nullable=True))
    op.add_column('customers', sa.Column('pendency', sa.String(length=50), nullable=True))


def downgrade():
    """Remove the new customer fields"""
    
    op.drop_column('customers', 'pendency')
    op.drop_column('customers', 'pending_amount')
    op.drop_column('customers', 'salary_last_date')
    op.drop_column('customers', 'cbs_income_verification')
    op.drop_column('customers', 'employment_status')
    op.drop_column('customers', 'days_since_employment')
    op.drop_column('customers', 'cibil_score')
