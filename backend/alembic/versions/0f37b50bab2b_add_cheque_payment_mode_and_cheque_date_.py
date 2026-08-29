"""add cheque payment mode and cheque date columns

Revision ID: 0f37b50bab2b
Revises: d102dc26c3b2
Create Date: 2026-07-24 11:14:35.479335

"""
import sys
from pathlib import Path
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _helpers import column_exists  # noqa: E402

# revision identifiers, used by Alembic.
revision: str = '0f37b50bab2b'
down_revision: Union[str, Sequence[str], None] = 'd102dc26c3b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ALTER TYPE ... ADD VALUE cannot run inside the same transaction that
    # might use the new value — same reason as the earlier 'pending' status migration.
    # IF NOT EXISTS already makes this safe on a fresh install where
    # schema.sql's baseline CREATE TYPE already includes 'cheque'.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE payment_mode ADD VALUE IF NOT EXISTS 'cheque'")

    # These two columns are already in backend/db/schema.sql's baseline
    # (edited in after this migration was written), so guarded to stay a
    # no-op on a fresh install.
    bind = op.get_bind()
    if not column_exists(bind, "payment_collections", "cheque_given_date"):
        op.add_column("payment_collections", sa.Column("cheque_given_date", sa.Date(), nullable=True))
    if not column_exists(bind, "payment_collections", "cheque_deposit_date"):
        op.add_column("payment_collections", sa.Column("cheque_deposit_date", sa.Date(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("payment_collections", "cheque_deposit_date")
    op.drop_column("payment_collections", "cheque_given_date")
    # Postgres has no ALTER TYPE ... DROP VALUE — not reversible, same as
    # the earlier payment_status 'pending' addition.
