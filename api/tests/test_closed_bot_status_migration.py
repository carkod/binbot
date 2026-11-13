from io import StringIO
import os
from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, text

from api.alembic.versions import b7e21d4c9a60_add_closed_bot_status as migration


def test_closed_enum_upgrade_is_guarded_and_downgrade_preserves_archives(monkeypatch):
    sql = StringIO()
    context = MigrationContext.configure(
        dialect_name="postgresql", opts={"as_sql": True, "output_buffer": sql}
    )
    monkeypatch.setattr(migration, "op", Operations(context))
    migration.upgrade()
    assert "ALTER TYPE status ADD VALUE IF NOT EXISTS 'closed'" in sql.getvalue()
    sql.truncate(0)
    sql.seek(0)
    migration.downgrade()
    assert sql.getvalue() == ""


@pytest.mark.parametrize("already_migrated", [False, True])
def test_closed_enum_migration_replays_on_postgres(monkeypatch, already_migrated):
    url = os.getenv("TEST_POSTGRES_URL")
    if not url:
        pytest.skip("Set TEST_POSTGRES_URL to run PostgreSQL enum migration tests")
    engine = create_engine(url)
    schema = f"closed_status_{uuid4().hex}"
    try:
        with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            conn.execute(text(f'CREATE SCHEMA "{schema}"'))
            try:
                conn.execute(text(f'SET search_path TO "{schema}"'))
                values = "'inactive', 'pending', 'active', 'completed', 'error'"
                if already_migrated:
                    values += ", 'closed'"
                conn.execute(text(f"CREATE TYPE status AS ENUM ({values})"))
                conn.execute(
                    text("CREATE TABLE bot (id INTEGER PRIMARY KEY, status status)")
                )
                conn.execute(text("INSERT INTO bot VALUES (1, 'pending')"))
                if already_migrated:
                    conn.execute(text("INSERT INTO bot VALUES (2, 'closed')"))
                monkeypatch.setattr(
                    migration, "op", Operations(MigrationContext.configure(conn))
                )
                migration.upgrade()
                migration.upgrade()
                conn.execute(text("UPDATE bot SET status = 'closed' WHERE id = 1"))
                migration.downgrade()
                migration.upgrade()
                rows = (
                    conn.execute(text("SELECT status::text FROM bot ORDER BY id"))
                    .scalars()
                    .all()
                )
                assert rows == ["closed"] * (2 if already_migrated else 1)
            finally:
                conn.execute(text("SET search_path TO public"))
                conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
    finally:
        engine.dispose()
