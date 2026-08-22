"""drop trips online_amount, moved to per-shop entries

Revision ID: c31539f26ce9
Revises: bc5c59d1df03
Create Date: 2026-07-23 19:57:44.297856

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c31539f26ce9'
down_revision: Union[str, Sequence[str], None] = 'bc5c59d1df03'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_column('trips', 'online_amount')


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column(
        'trips',
        sa.Column('online_amount', sa.Numeric(precision=14, scale=2), server_default=sa.text('0'), nullable=False),
    )
