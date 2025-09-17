"""merge_heads

Revision ID: 3e65269518d4
Revises: 004_add_policy_rule_fields, aefd4c279334
Create Date: 2025-09-17 20:53:45.166602

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3e65269518d4'
down_revision: Union[str, None] = ('004_add_policy_rule_fields', 'aefd4c279334')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
