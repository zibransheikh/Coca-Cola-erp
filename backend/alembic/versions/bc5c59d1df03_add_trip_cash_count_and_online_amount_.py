"""add trip cash count and online amount fields

Revision ID: bc5c59d1df03
Revises: 49d7ed2b9dfb
Create Date: 2026-07-23 19:08:49.560203

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'bc5c59d1df03'
down_revision: Union[str, Sequence[str], None] = '49d7ed2b9dfb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('trips', sa.Column('cash_count_500', sa.BigInteger(), server_default=sa.text('0'), nullable=False))
    op.add_column('trips', sa.Column('cash_count_200', sa.BigInteger(), server_default=sa.text('0'), nullable=False))
    op.add_column('trips', sa.Column('cash_count_100', sa.BigInteger(), server_default=sa.text('0'), nullable=False))
    op.add_column('trips', sa.Column('cash_count_50', sa.BigInteger(), server_default=sa.text('0'), nullable=False))
    op.add_column('trips', sa.Column('cash_count_20', sa.BigInteger(), server_default=sa.text('0'), nullable=False))
    op.add_column('trips', sa.Column('cash_count_10', sa.BigInteger(), server_default=sa.text('0'), nullable=False))
    op.add_column(
        'trips',
        sa.Column('cash_coins_amount', sa.Numeric(precision=14, scale=2), server_default=sa.text('0'), nullable=False),
    )
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
