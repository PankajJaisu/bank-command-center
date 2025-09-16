"""add_description_to_automation_rules

Revision ID: aefd4c279334
Revises: 003_add_customer_fields
Create Date: 2025-08-18 17:43:10.225044

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'aefd4c279334'
down_revision: Union[str, None] = '003_add_customer_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add description column to automation_rules table
    op.add_column('automation_rules', sa.Column('description', sa.Text(), nullable=True))


def downgrade() -> None:
    # Remove description column from automation_rules table
    op.drop_column('automation_rules', 'description')
