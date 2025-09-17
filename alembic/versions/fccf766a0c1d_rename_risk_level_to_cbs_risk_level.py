"""rename_risk_level_to_cbs_risk_level

Revision ID: fccf766a0c1d
Revises: 3e65269518d4
Create Date: 2025-09-17 20:53:55.350079

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fccf766a0c1d'
down_revision: Union[str, None] = '3e65269518d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # SQLite doesn't support column renaming directly, so we need to:
    # 1. Add the new column
    # 2. Copy data from old column to new column
    # 3. Drop the old column (but SQLite doesn't support this either)
    # So we'll just add the new column and copy the data
    
    # Add the new cbs_risk_level column
    op.add_column('customers', sa.Column('cbs_risk_level', sa.String(length=100), nullable=True))
    
    # Copy data from risk_level to cbs_risk_level
    op.execute("UPDATE customers SET cbs_risk_level = risk_level")


def downgrade() -> None:
    # Copy data back from cbs_risk_level to risk_level
    op.execute("UPDATE customers SET risk_level = cbs_risk_level")
    
    # Drop the cbs_risk_level column
    op.drop_column('customers', 'cbs_risk_level')
