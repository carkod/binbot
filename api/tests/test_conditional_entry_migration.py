import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text

from api.alembic.versions import f9c2a617d83e_conditional_bot_entry as migration


@pytest.mark.parametrize(
    "existing_columns",
    [(), ("entry_mode",), ("entry_mode", "entry_price", "entry_expires_at")],
)
def test_entry_migration_backfills_and_replays_without_overwriting_configuration(
    monkeypatch, existing_columns
):
    with create_engine("sqlite://").begin() as connection:
        connection.execute(
            text("CREATE TABLE bot (id TEXT PRIMARY KEY, created_at FLOAT NOT NULL)")
        )
        connection.execute(
            text("INSERT INTO bot VALUES ('legacy', 1000), ('configured', 2000)")
        )
        for column in existing_columns:
            kind = "TEXT" if column == "entry_mode" else "FLOAT"
            connection.execute(text(f"ALTER TABLE bot ADD COLUMN {column} {kind}"))
        if "entry_mode" in existing_columns:
            connection.execute(
                text(
                    "UPDATE bot SET entry_mode = 'conditional_limit' WHERE id = 'configured'"
                )
            )
        if "entry_expires_at" in existing_columns:
            connection.execute(
                text(
                    "UPDATE bot SET entry_price = 123, entry_expires_at = 99999 WHERE id = 'configured'"
                )
            )
        monkeypatch.setattr(
            migration, "op", Operations(MigrationContext.configure(connection))
        )
        migration.upgrade()
        migration.upgrade()
        rows = connection.execute(
            text(
                "SELECT entry_mode, entry_price, entry_expires_at FROM bot ORDER BY id"
            )
        ).all()
        assert rows[1] == ("immediate", None, 21_601_000)
        assert rows[0] == (
            "conditional_limit" if existing_columns else "immediate",
            123 if "entry_price" in existing_columns else None,
            99999 if "entry_expires_at" in existing_columns else 21_602_000,
        )
        columns = {
            column["name"]: column for column in inspect(connection).get_columns("bot")
        }
        assert columns["entry_price"]["nullable"]
        assert columns["entry_price"]["default"] is None
        assert not columns["entry_mode"]["nullable"]
        assert not columns["entry_expires_at"]["nullable"]
        migration.downgrade()
        migration.downgrade()
        assert {
            column["name"] for column in inspect(connection).get_columns("bot")
        } == {"id", "created_at"}


def test_entry_migration_removes_previous_nonnullable_price_default(monkeypatch):
    with create_engine("sqlite://").begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE bot (id TEXT PRIMARY KEY, created_at FLOAT NOT NULL, "
                "entry_price FLOAT NOT NULL DEFAULT 0)"
            )
        )
        connection.execute(
            text(
                "INSERT INTO bot (id, created_at, entry_price) VALUES ('configured', 1000, 123)"
            )
        )
        monkeypatch.setattr(
            migration, "op", Operations(MigrationContext.configure(connection))
        )
        migration.upgrade()
        migration.upgrade()
        connection.execute(
            text(
                "INSERT INTO bot (id, created_at, entry_expires_at) VALUES ('new', 1000, 21601000)"
            )
        )
        assert connection.execute(
            text("SELECT entry_price FROM bot ORDER BY id")
        ).scalars().all() == [123, None]
