from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings

# prepare_threshold=None disables psycopg3's automatic server-side prepared
# statements, which don't survive Neon's PgBouncer connection pooler
# (transaction mode hands each transaction a different backend connection).
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    connect_args={"prepare_threshold": None},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    # db/schema.sql uses BIGINT identity PKs, TEXT columns, and TIMESTAMPTZ
    # everywhere (see docs/database-design.md); without this, SQLAlchemy's
    # bare `Mapped[int]`/`Mapped[str]`/`Mapped[datetime]` default to
    # INTEGER/VARCHAR/naive DateTime, which makes every future `alembic
    # revision --autogenerate` report spurious type-change noise against the
    # real schema. A column that genuinely needs to differ (e.g. the
    # INTEGER `credit_days` day-count) overrides this explicitly.
    type_annotation_map = {
        int: BigInteger,
        str: Text,
        datetime: DateTime(timezone=True),
    }


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
