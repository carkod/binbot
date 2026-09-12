from unittest.mock import MagicMock

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text

from api.alembic.versions import (
    b8c9d0e1f2a3_repair_current_position_qty,
    e6f7a8b9c0d1_add_gainers_losers_series_source,
)
from api.databases import api_db


def test_repair_current_position_qty_adds_and_backfills_column(monkeypatch):
    engine = create_engine("sqlite://")

    with engine.begin() as connection:
        connection.execute(
            text("CREATE TABLE deal (id TEXT PRIMARY KEY, opening_qty FLOAT NOT NULL)")
        )
        connection.execute(
            text("CREATE TABLE bot (deal_id TEXT, status TEXT NOT NULL)")
        )
        connection.execute(
            text("CREATE TABLE paper_trading (deal_id TEXT, status TEXT NOT NULL)")
        )
        connection.execute(
            text(
                """
                INSERT INTO deal (id, opening_qty)
                VALUES ('active', 5), ('completed', 4), ('paper', 3), ('flat', 0)
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO bot (deal_id, status)
                VALUES ('active', 'active'), ('completed', 'completed'), ('flat', 'active')
                """
            )
        )
        connection.execute(
            text(
                "INSERT INTO paper_trading (deal_id, status) VALUES ('paper', 'pending')"
            )
        )

        operations = Operations(MigrationContext.configure(connection))
        monkeypatch.setattr(
            b8c9d0e1f2a3_repair_current_position_qty,
            "op",
            operations,
        )

        b8c9d0e1f2a3_repair_current_position_qty.upgrade()
        b8c9d0e1f2a3_repair_current_position_qty.upgrade()

        columns = {
            column["name"]: column for column in inspect(connection).get_columns("deal")
        }
        assert columns["current_position_qty"]["nullable"] is False

        rows = connection.execute(
            text("SELECT id, current_position_qty FROM deal ORDER BY id")
        ).all()
        assert rows == [
            ("active", 5.0),
            ("completed", 0.0),
            ("flat", 0.0),
            ("paper", 3.0),
        ]

        b8c9d0e1f2a3_repair_current_position_qty.downgrade()
        assert "current_position_qty" in {
            column["name"] for column in inspect(connection).get_columns("deal")
        }


def test_gainers_losers_source_migration_can_replay_completed_schema(monkeypatch):
    operations = MagicMock()
    inspector = MagicMock()
    inspector.get_columns.return_value = [{"name": "source"}]
    inspector.get_indexes.return_value = [
        {"name": "ix_top_gainers_losers_series_source"}
    ]
    inspector.get_unique_constraints.return_value = [
        {"name": ("uq_top_gainers_losers_series_source_recorded_at_side_rank")}
    ]
    monkeypatch.setattr(
        e6f7a8b9c0d1_add_gainers_losers_series_source,
        "op",
        operations,
    )
    monkeypatch.setattr(
        e6f7a8b9c0d1_add_gainers_losers_series_source.sa,
        "inspect",
        lambda _: inspector,
    )

    e6f7a8b9c0d1_add_gainers_losers_series_source.upgrade()

    operations.add_column.assert_not_called()
    operations.create_index.assert_not_called()
    operations.drop_constraint.assert_not_called()
    operations.create_unique_constraint.assert_not_called()


def test_run_migrations_preserves_legitimate_branch_revisions(monkeypatch):
    connection = MagicMock()
    connection.execute.return_value = [
        ("615975c99625",),
        ("e6f7a8b9c0d1",),
    ]
    engine = MagicMock()
    engine.connect.return_value.__enter__.return_value = connection
    alembic_config = MagicMock()
    script_directory = MagicMock()
    script_directory.get_heads.return_value = ["b8c9d0e1f2a3"]
    upgrade = MagicMock()

    monkeypatch.setattr(api_db, "engine", engine)
    monkeypatch.setattr(api_db, "Config", lambda _: alembic_config)
    monkeypatch.setattr(
        api_db.ScriptDirectory,
        "from_config",
        lambda _: script_directory,
    )
    monkeypatch.setattr(api_db.command, "upgrade", upgrade)

    instance = object.__new__(api_db.ApiDb)
    instance.run_migrations()

    assert connection.execute.call_count == 1
    assert "SELECT version_num FROM alembic_version" in str(
        connection.execute.call_args.args[0]
    )
    upgrade.assert_called_once_with(alembic_config, "heads")
