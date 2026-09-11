"""add current position quantity

Revision ID: a7b8c9d0e1f2
Revises: 615975c99625, e6f7a8b9c0d1
Create Date: 2026-09-11

"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "a7b8c9d0e1f2"
down_revision: str | Sequence[str] | None = (
    "615975c99625",
    "e6f7a8b9c0d1",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
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
                  AND bot.status::text IN ('active', 'pending')
            )
            OR EXISTS (
                SELECT 1
                FROM paper_trading
                WHERE paper_trading.deal_id = deal.id
                  AND paper_trading.status::text IN ('active', 'pending')
            )
          )
        """
    )


def downgrade() -> None:
    op.drop_column("deal", "current_position_qty")
