"""keep error grid ladders active until exchange recovery completes

Revision ID: b1c2d3e4f5a6
Revises: a0e265d5cb35
"""

from collections.abc import Sequence

from alembic import op
from sqlalchemy import text

revision: str = "b1c2d3e4f5a6"
down_revision: str | Sequence[str] | None = "a0e265d5cb35"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        WITH ranked_ladders AS (
            SELECT
                id,
                status,
                ROW_NUMBER() OVER (
                    PARTITION BY symbol
                    ORDER BY
                        CASE
                            WHEN status IN ('pending', 'active', 'closing') THEN 0
                            ELSE 1
                        END,
                        created_at DESC,
                        updated_at DESC,
                        id DESC
                ) AS active_rank
            FROM grid_ladder
            WHERE status IN ('pending', 'active', 'closing', 'error')
        )
        UPDATE grid_ladder
        SET
            status = 'closed',
            closed_at = COALESCE(closed_at, updated_at, created_at)
        WHERE id IN (
            SELECT id
            FROM ranked_ladders
            WHERE status = 'error' AND active_rank > 1
        )
        """
    )
    op.drop_index("ix_grid_ladder_active_symbol", table_name="grid_ladder")
    op.create_index(
        "ix_grid_ladder_active_symbol",
        "grid_ladder",
        ["symbol"],
        unique=True,
        postgresql_where=text("status IN ('pending', 'active', 'closing', 'error')"),
        sqlite_where=text("status IN ('pending', 'active', 'closing', 'error')"),
    )


def downgrade() -> None:
    op.drop_index("ix_grid_ladder_active_symbol", table_name="grid_ladder")
    op.create_index(
        "ix_grid_ladder_active_symbol",
        "grid_ladder",
        ["symbol"],
        unique=True,
        postgresql_where=text("status IN ('pending', 'active', 'closing')"),
        sqlite_where=text("status IN ('pending', 'active', 'closing')"),
    )
