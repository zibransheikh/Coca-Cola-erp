"""drop trips crates_out, now computed from stock sheet

Revision ID: db957068be64
Revises: 0f37b50bab2b
Create Date: 2026-07-24 19:06:54.326350

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'db957068be64'
down_revision: Union[str, Sequence[str], None] = '0f37b50bab2b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_column("trips", "crates_out")


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column("trips", sa.Column("crates_out", sa.BigInteger(), server_default=sa.text("0"), nullable=False))
