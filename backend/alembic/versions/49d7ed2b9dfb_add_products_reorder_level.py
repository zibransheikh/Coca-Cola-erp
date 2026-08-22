"""add products reorder_level

Revision ID: 49d7ed2b9dfb
Revises: 8915dcd435d2
Create Date: 2026-07-22 22:23:19.494257

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '49d7ed2b9dfb'
down_revision: Union[str, Sequence[str], None] = '8915dcd435d2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'products',
        sa.Column(
            'reorder_level',
            sa.Numeric(precision=14, scale=3),
            server_default=sa.text('0'),
            nullable=False,
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('products', 'reorder_level')
