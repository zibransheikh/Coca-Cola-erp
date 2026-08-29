"""Shared helpers for migrations that may run against a database bootstrapped
from a version of backend/db/schema.sql that already includes the column/table
being added (the baseline migration re-reads schema.sql live, so edits to it
after a later migration was written can make that migration redundant on a
fresh install, while still needed on databases from before the edit).
"""
from sqlalchemy import text
from sqlalchemy.engine import Connection


def column_exists(bind: Connection, table: str, column: str) -> bool:
    row = bind.execute(
        text(
            "select 1 from information_schema.columns "
            "where table_name = :table and column_name = :column"
        ),
        {"table": table, "column": column},
    ).first()
    return row is not None


def table_exists(bind: Connection, table: str) -> bool:
    row = bind.execute(
        text("select 1 from information_schema.tables where table_name = :table"),
        {"table": table},
    ).first()
    return row is not None
