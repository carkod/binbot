"""repair current position quantity

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-09-12

"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "b8c9d0e1f2a3"
down_revision: str | Sequence[str] | None = "a7b8c9d0e1f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("deal")}

    if "current_position_qty" not in columns:
        op.add_column(
            "deal",
            sa.Column(
                "current_position_qty",
                sa.Float(),
                nullable=False,
                server_default=sa.text("0"),
            ),
        )

    op.execute(
        """
        UPDATE deal
        SET current_position_qty = deal.opening_qty
        WHERE deal.opening_qty > 0
          AND (
            EXISTS (
                SELECT 1
                FROM bot
                WHERE bot.deal_id = deal.id
                  AND CAST(bot.status AS VARCHAR) IN ('active', 'pending')
            )
            OR EXISTS (
                SELECT 1
                FROM paper_trading
                WHERE paper_trading.deal_id = deal.id
                  AND CAST(paper_trading.status AS VARCHAR) IN ('active', 'pending')
            )
          )
        """
    )


def downgrade() -> None:
    # Revision a7b8c9d0e1f2 owns the column; this repair must not remove it.
    pass
