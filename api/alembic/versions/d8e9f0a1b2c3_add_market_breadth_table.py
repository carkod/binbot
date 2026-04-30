"""Add market_breadth table (replaces Mongo kafka_db.market_breadth)

Revision ID: d8e9f0a1b2c3
Revises: e4a3a439c266
Create Date: 2026-04-30 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d8e9f0a1b2c3"
down_revision: Union[str, Sequence[str], None] = "e4a3a439c266"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "market_breadth",
        sa.Column(
            "id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False
        ),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("advancers", sa.Integer(), nullable=False),
        sa.Column("decliners", sa.Integer(), nullable=False),
        sa.Column("adp", sa.Float(), nullable=False),
        sa.Column("avg_gain", sa.Float(), nullable=False),
        sa.Column("avg_loss", sa.Float(), nullable=False),
        sa.Column("total_volume", sa.Float(), nullable=False),
        sa.Column("strength_index", sa.Float(), nullable=False),
        sa.UniqueConstraint("timestamp", "source", name="uq_market_breadth_ts_source"),
    )
    op.create_index(
        "ix_market_breadth_timestamp", "market_breadth", ["timestamp"], unique=False
    )
    op.create_index(
        "ix_market_breadth_source", "market_breadth", ["source"], unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_market_breadth_source", table_name="market_breadth")
    op.drop_index("ix_market_breadth_timestamp", table_name="market_breadth")
    op.drop_table("market_breadth")
