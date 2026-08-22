"""add trips crates_out and crates_in

Revision ID: d102dc26c3b2
Revises: 350c6f46ff9f
Create Date: 2026-07-24 11:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'd102dc26c3b2'
down_revision: Union[str, Sequence[str], None] = '350c6f46ff9f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('trips', sa.Column('crates_out', sa.BigInteger(), server_default=sa.text('0'), nullable=False))
    op.add_column('trips', sa.Column('crates_in', sa.BigInteger(), server_default=sa.text('0'), nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('trips', 'crates_in')
    op.drop_column('trips', 'crates_out')
