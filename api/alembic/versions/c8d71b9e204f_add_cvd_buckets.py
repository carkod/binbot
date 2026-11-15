"""Store execution notionals and coverage independently of trading loops."""

from alembic import op
import sqlalchemy as sa
from typing import Any

revision = "c8d71b9e204f"
down_revision = "b7e21d4c9a60"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Keep migration schema independent of future application model changes.
    bind = op.get_bind()
    definitions: list[tuple[str, list[sa.Column[Any]]]] = [
        (
            "cvd_bucket",
            [
                sa.Column("symbol", sa.String(64), primary_key=True),
                sa.Column("multiplier", sa.Float(), nullable=False, server_default="0"),
                sa.Column(
                    "covered", sa.Boolean(), nullable=False, server_default=sa.false()
                ),
                sa.Column(
                    "last_trade_ns", sa.BigInteger(), nullable=False, server_default="0"
                ),
            ],
        ),
        (
            "cvd_minute",
            [
                sa.Column(
                    "expected_symbols", sa.Integer(), nullable=False, server_default="0"
                ),
                sa.Column(
                    "covered_symbols", sa.Integer(), nullable=False, server_default="0"
                ),
                sa.Column(
                    "universe", sa.String(64), nullable=False, server_default="unknown"
                ),
                sa.Column(
                    "finalized", sa.Boolean(), nullable=False, server_default=sa.false()
                ),
                sa.Column(
                    "updated_at",
                    sa.DateTime(timezone=True),
                    nullable=False,
                    server_default=sa.func.now(),
                ),
            ],
        ),
    ]
    for name, extra_columns in definitions:
        columns: list[sa.Column[Any]] = [
            sa.Column("source", sa.String(32), primary_key=True),
            sa.Column("minute", sa.BigInteger(), primary_key=True),
            sa.Column("buy", sa.Float(), nullable=False, server_default="0"),
            sa.Column("sell", sa.Float(), nullable=False, server_default="0"),
            *extra_columns,
        ]
        if not sa.inspect(bind).has_table(name):
            op.create_table(name, *columns)
        else:
            existing = {c["name"] for c in sa.inspect(bind).get_columns(name)}
            for column in columns:
                if column.name not in existing:
                    op.add_column(name, column)
        index_name = f"ix_{name}_minute"
        if index_name not in {i["name"] for i in sa.inspect(bind).get_indexes(name)}:
            op.create_index(index_name, name, ["minute"])


def downgrade() -> None:
    for name in ("cvd_bucket", "cvd_minute"):
        if sa.inspect(op.get_bind()).has_table(name):
            op.drop_table(name)
