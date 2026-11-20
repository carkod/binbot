"""Remove the global autotrade candle interval; consumers default to 15m."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ENUM

revision = "a9d38e21c6f4"
down_revision = "c8d71b9e204f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    for table in ("autotrade", "test_autotrade"):
        inspector = sa.inspect(bind)
        if inspector.has_table(table) and "candlestick_interval" in {
            column["name"] for column in inspector.get_columns(table)
        }:
            op.drop_column(table, "candlestick_interval")


def downgrade() -> None:
    bind = op.get_bind()
    # Reuse the enum retained by bot.candlestick_interval. Previous choices
    # cannot be recovered, so restored settings use the 15-minute default.
    interval_type = ENUM(name="binanceklineintervals", create_type=False)
    for table in ("autotrade", "test_autotrade"):
        inspector = sa.inspect(bind)
        if inspector.has_table(table) and "candlestick_interval" not in {
            column["name"] for column in inspector.get_columns(table)
        }:
            op.add_column(
                table,
                sa.Column(
                    "candlestick_interval",
                    interval_type if bind.dialect.name == "postgresql" else sa.String(),
                    nullable=True,
                    server_default="fifteen_minutes",
                ),
            )
