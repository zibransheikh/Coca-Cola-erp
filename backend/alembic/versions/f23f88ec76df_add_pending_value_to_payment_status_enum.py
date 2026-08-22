"""add pending value to payment_status enum

Revision ID: f23f88ec76df
Revises: c31539f26ce9
Create Date: 2026-07-23 21:04:12.597657

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f23f88ec76df'
down_revision: Union[str, Sequence[str], None] = 'c31539f26ce9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ALTER TYPE ... ADD VALUE cannot run inside the same transaction that
    # might use the new value, so this needs its own autocommit block.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE payment_status ADD VALUE IF NOT EXISTS 'pending'")


def downgrade() -> None:
    """Downgrade schema."""
    # Postgres has no ALTER TYPE ... DROP VALUE — removing an enum value
    # cleanly would mean rebuilding the type and every column using it.
    # Not reversible; left as a no-op like other additive enum changes.
    pass
