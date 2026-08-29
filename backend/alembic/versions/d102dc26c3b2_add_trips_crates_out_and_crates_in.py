"""add trips crates_out and crates_in

Revision ID: d102dc26c3b2
Revises: 350c6f46ff9f
Create Date: 2026-07-24 11:20:00.000000

"""
import sys
from pathlib import Path
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _helpers import column_exists  # noqa: E402

# revision identifiers, used by Alembic.
revision: str = 'd102dc26c3b2'
down_revision: Union[str, Sequence[str], None] = '350c6f46ff9f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # crates_out is added here, then dropped a few migrations later
    # (db957068be64) once it became a computed value — kept unconditional so
    # that later drop still has a column to drop. crates_in is already in
    # backend/db/schema.sql's baseline, so it's guarded to stay a no-op on a
    # fresh install.
    op.add_column('trips', sa.Column('crates_out', sa.BigInteger(), server_default=sa.text('0'), nullable=False))
    bind = op.get_bind()
    if not column_exists(bind, 'trips', 'crates_in'):
        op.add_column('trips', sa.Column('crates_in', sa.BigInteger(), server_default=sa.text('0'), nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('trips', 'crates_in')
    op.drop_column('trips', 'crates_out')
