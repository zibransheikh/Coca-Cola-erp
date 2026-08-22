"""backfill existing credit collections to pending status

Revision ID: 309ad193a1f3
Revises: f23f88ec76df
Create Date: 2026-07-23 21:07:55.590363

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '309ad193a1f3'
down_revision: Union[str, Sequence[str], None] = 'f23f88ec76df'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Existing credit-mode rows have status='cleared' from the old flow,
    # where 'cleared' only ever meant "this collection record needs no bank
    # verification" — it never meant "the shop has repaid this credit" since
    # that concept didn't exist yet. Backfill them to 'pending' so status
    # means the same thing for every credit row: has it been marked repaid
    # via the app. Nothing else reads payment_collections.status for credit
    # mode (outstanding balances come from customer_ledger), so this is safe.
    op.execute("UPDATE payment_collections SET status = 'pending' WHERE payment_mode = 'credit' AND status = 'cleared'")


def downgrade() -> None:
    """Downgrade schema."""
    # Not reversible: can't tell which rows were 'cleared' before this ran
    # versus genuinely marked paid afterward.
    pass
