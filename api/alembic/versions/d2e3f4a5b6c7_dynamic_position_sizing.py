"""Persist opt-in dynamic sizing and in-flight adjustments."""

import sqlalchemy as sa
from alembic import op

revision = "d2e3f4a5b6c7"
down_revision = "c1d2e3f4a5b6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    for table, name, column_type, default in (
        ("bot", "dynamic_position_sizing", sa.Boolean(), sa.false()),
        ("paper_trading", "dynamic_position_sizing", sa.Boolean(), sa.false()),
        ("deal", "position_size_pct", sa.Float(), sa.text("25")),
        ("deal", "position_size_reference_price", sa.Float(), sa.text("0")),
        ("deal", "position_size_order", sa.JSON(), None),
    ):
        columns = {c["name"] for c in sa.inspect(bind).get_columns(table)}
        if name not in columns:
            op.add_column(
                table,
                sa.Column(
                    name, column_type, nullable=default is None, server_default=default
                ),
            )
        if default is not None:
            target = sa.table(table, sa.column(name, column_type))
            bind.execute(
                target.update().where(target.c[name].is_(None)).values({name: default})
            )


def downgrade() -> None:
    for table, names in (
        ("bot", ("dynamic_position_sizing",)),
        ("paper_trading", ("dynamic_position_sizing",)),
        (
            "deal",
            (
                "position_size_pct",
                "position_size_reference_price",
                "position_size_order",
            ),
        ),
    ):
        columns = {c["name"] for c in sa.inspect(op.get_bind()).get_columns(table)}
        for name in names:
            if name in columns:
                op.drop_column(table, name)
