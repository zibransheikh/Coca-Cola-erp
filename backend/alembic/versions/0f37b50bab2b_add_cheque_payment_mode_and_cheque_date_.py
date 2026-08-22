"""add cheque payment mode and cheque date columns

Revision ID: 0f37b50bab2b
Revises: d102dc26c3b2
Create Date: 2026-07-24 11:14:35.479335

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0f37b50bab2b'
down_revision: Union[str, Sequence[str], None] = 'd102dc26c3b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ALTER TYPE ... ADD VALUE cannot run inside the same transaction that
    # might use the new value — same reason as the earlier 'pending' status migration.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE payment_mode ADD VALUE IF NOT EXISTS 'cheque'")

    op.add_column("payment_collections", sa.Column("cheque_given_date", sa.Date(), nullable=True))
    op.add_column("payment_collections", sa.Column("cheque_deposit_date", sa.Date(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("payment_collections", "cheque_deposit_date")
    op.drop_column("payment_collections", "cheque_given_date")
    # Postgres has no ALTER TYPE ... DROP VALUE — not reversible, same as
    # the earlier payment_status 'pending' addition.
