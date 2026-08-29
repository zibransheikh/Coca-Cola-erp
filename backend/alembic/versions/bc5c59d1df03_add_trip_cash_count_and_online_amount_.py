"""add trip cash count and online amount fields

Revision ID: bc5c59d1df03
Revises: 49d7ed2b9dfb
Create Date: 2026-07-23 19:08:49.560203

"""
import sys
from pathlib import Path
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _helpers import column_exists  # noqa: E402

# revision identifiers, used by Alembic.
revision: str = 'bc5c59d1df03'
down_revision: Union[str, Sequence[str], None] = '49d7ed2b9dfb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # The cash_count_*/cash_coins_amount columns are already in backend/db/
    # schema.sql's baseline (edited in after this migration was written), so
    # they're guarded to stay no-ops on a fresh install. online_amount was
    # since superseded by per-shop payment_collections rows and was never
    # added to schema.sql, so it still needs adding here unconditionally on
    # a fresh install too — kept for existing databases that have it.
    bind = op.get_bind()
    for column, coltype in [
        ('cash_count_500', sa.BigInteger()),
        ('cash_count_200', sa.BigInteger()),
        ('cash_count_100', sa.BigInteger()),
        ('cash_count_50', sa.BigInteger()),
        ('cash_count_20', sa.BigInteger()),
        ('cash_count_10', sa.BigInteger()),
        ('cash_coins_amount', sa.Numeric(precision=14, scale=2)),
    ]:
        if not column_exists(bind, 'trips', column):
            op.add_column(
                'trips', sa.Column(column, coltype, server_default=sa.text('0'), nullable=False)
            )
    if not column_exists(bind, 'trips', 'online_amount'):
        op.add_column(
            'trips',
            sa.Column('online_amount', sa.Numeric(precision=14, scale=2), server_default=sa.text('0'), nullable=False),
        )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('trips', 'online_amount')
    op.drop_column('trips', 'cash_coins_amount')
    op.drop_column('trips', 'cash_count_10')
    op.drop_column('trips', 'cash_count_20')
    op.drop_column('trips', 'cash_count_50')
    op.drop_column('trips', 'cash_count_100')
    op.drop_column('trips', 'cash_count_200')
    op.drop_column('trips', 'cash_count_500')
