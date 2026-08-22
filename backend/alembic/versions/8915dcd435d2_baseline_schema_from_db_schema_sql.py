"""baseline schema from db/schema.sql

Revision ID: 8915dcd435d2
Revises: 
Create Date: 2026-07-21 23:35:06.188893

"""
from pathlib import Path
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8915dcd435d2'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# The full, hand-designed and independently-validated schema lives in
# db/schema.sql (see docs/database-design.md for the rationale). This baseline
# migration applies it verbatim rather than re-deriving it from ORM models, so
# it stays the single source of truth for the physical schema. Only the
# auth/RBAC/audit tables are ORM-modeled so far; later phases add models (and
# ordinary autogenerate migrations) for the rest as those modules get built.
SCHEMA_SQL_PATH = Path(__file__).resolve().parents[3] / "db" / "schema.sql"


def upgrade() -> None:
    sql = SCHEMA_SQL_PATH.read_text()
    op.execute(sql)


def downgrade() -> None:
    op.execute("DROP SCHEMA public CASCADE;")
    op.execute("CREATE SCHEMA public;")
