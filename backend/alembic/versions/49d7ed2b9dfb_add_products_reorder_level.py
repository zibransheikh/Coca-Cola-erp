"""add products reorder_level

Revision ID: 49d7ed2b9dfb
Revises: 8915dcd435d2
Create Date: 2026-07-22 22:23:19.494257

"""
import sys
from pathlib import Path
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _helpers import column_exists  # noqa: E402

# revision identifiers, used by Alembic.
revision: str = '49d7ed2b9dfb'
down_revision: Union[str, Sequence[str], None] = '8915dcd435d2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # backend/db/schema.sql's baseline (revision 8915dcd435d2) already
    # includes this column as of a later edit to that file — the baseline
    # migration re-reads schema.sql live rather than a frozen snapshot, so a
    # fresh install applying both migrations in sequence would otherwise hit
    # a duplicate-column error. Guard so this stays a no-op on fresh installs
    # while still applying on existing databases from before that edit.
    bind = op.get_bind()
    if not column_exists(bind, 'products', 'reorder_level'):
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
