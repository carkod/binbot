from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, text

from api.alembic.versions import b1c2d3e4f5a6_keep_error_grid_ladders_active


def test_error_ladder_unique_index_migration_closes_superseded_rows(monkeypatch):
    engine = create_engine("sqlite://")

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE grid_ladder (
                    id TEXT PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at FLOAT NOT NULL,
                    updated_at FLOAT NOT NULL,
                    closed_at FLOAT
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE UNIQUE INDEX ix_grid_ladder_active_symbol
                ON grid_ladder (symbol)
                WHERE status IN ('pending', 'active', 'closing')
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO grid_ladder
                    (id, symbol, status, created_at, updated_at)
                VALUES
                    ('superseded-error', 'ADAUSDC', 'error', 1, 1),
                    ('current-active', 'ADAUSDC', 'active', 2, 2),
                    ('older-error', 'SOLUSDC', 'error', 1, 1),
                    ('newer-error', 'SOLUSDC', 'error', 2, 2)
                """
            )
        )

        operations = Operations(MigrationContext.configure(connection))
        monkeypatch.setattr(
            b1c2d3e4f5a6_keep_error_grid_ladders_active,
            "op",
            operations,
        )

        b1c2d3e4f5a6_keep_error_grid_ladders_active.upgrade()

        rows = connection.execute(
            text(
                """
                SELECT id, status, closed_at
                FROM grid_ladder
                ORDER BY id
                """
            )
        ).mappings()

        assert {row["id"]: (row["status"], row["closed_at"]) for row in rows} == {
            "current-active": ("active", None),
            "newer-error": ("error", None),
            "older-error": ("closed", 1.0),
            "superseded-error": ("closed", 1.0),
        }
