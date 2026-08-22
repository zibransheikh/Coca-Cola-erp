"""add products volume_ml

Revision ID: 350c6f46ff9f
Revises: 309ad193a1f3
Create Date: 2026-07-24 11:09:03.942045

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '350c6f46ff9f'
down_revision: Union[str, Sequence[str], None] = '309ad193a1f3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# SKU suffix -> volume in ml, used to backfill every product seeded so far
# (the default catalog's SKUs always end in one of these; ad-hoc test SKUs
# like the old "COKE-300"/"SPRITE-500" match on the bare numeric suffix too).
SUFFIX_TO_ML = [
    ("150ML", 150),
    ("200ML", 200),
    ("250ML", 250),
    ("300ML", 300),
    ("400ML", 400),
    ("500ML", 500),
    ("600ML", 600),
    ("750ML", 750),
    ("1-25L", 1250),
    ("1-5L", 1500),
    ("-1L", 1000),
    ("-2L", 2000),
    ("-300", 300),  # old test SKU "COKE-300"
    ("-500", 500),  # old test SKU "SPRITE-500"
]


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("products", sa.Column("volume_ml", sa.Numeric(precision=10, scale=2), nullable=True))

    conn = op.get_bind()
    for suffix, ml in SUFFIX_TO_ML:
        conn.execute(
            sa.text("UPDATE products SET volume_ml = :ml WHERE sku LIKE :pattern AND volume_ml IS NULL"),
            {"ml": ml, "pattern": f"%{suffix}"},
        )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("products", "volume_ml")
