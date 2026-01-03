"""generalize exchange order columns

Revision ID: 7775eb0b8c12
Revises: 1ba34823c751
Create Date: 2025-12-10 14:06:34.135474

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7775eb0b8c12"
down_revision: str | Sequence[str] | None = "1ba34823c751"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade():
    conn = op.get_bind()

    # tables to migrate
    tables = ["exchange_order", "fake_order"]

    for table in tables:
        # ---- 1. order_id: INT → VARCHAR ----
        op.add_column(table, sa.Column("order_id_temp", sa.String(), nullable=True))

        conn.execute(sa.text(f"UPDATE {table} SET order_id_temp = order_id::varchar"))

        op.drop_column(table, "order_id")
        op.alter_column(table, "order_id_temp", new_column_name="order_id")
        op.alter_column(table, "order_id", nullable=False)

        # ---- 2. order_type: Enum → VARCHAR ----
        op.execute(
            sa.text(
                f"ALTER TABLE {table} "
                f"ALTER COLUMN order_type TYPE varchar USING order_type::varchar"
            )
        )

        # ---- 3. order_side: Enum → VARCHAR ----
        op.execute(
            sa.text(
                f"ALTER TABLE {table} "
                f"ALTER COLUMN order_side TYPE varchar USING order_side::varchar"
            )
        )


def downgrade():
    conn = op.get_bind()

    # ORIGINAL ENUM values — replace with your real ones
    order_type_values = ("MARKET", "LIMIT", "STOP")
    order_side_values = ("BUY", "SELL")

    # recreate ENUM types
    op.execute(
        sa.text(
            "CREATE TYPE order_type_enum AS ENUM ("
            + ", ".join(f"'{v}'" for v in order_type_values)
            + ")"
        )
    )

    op.execute(
        sa.text(
            "CREATE TYPE order_side_enum AS ENUM ("
            + ", ".join(f"'{v}'" for v in order_side_values)
            + ")"
        )
    )

    tables = ["exchange_order", "fake_order"]

    for table in tables:
        # ---- 1. VARCHAR → INT (order_id) ----

        op.add_column(
            table,
            sa.Column("order_id_temp", sa.Integer(), nullable=True),
        )

        conn.execute(sa.text(f"UPDATE {table} SET order_id_temp = order_id::integer"))

        op.drop_column(table, "order_id")
        op.alter_column(table, "order_id_temp", new_column_name="order_id")
        op.alter_column(table, "order_id", nullable=False)

        # ---- 2. VARCHAR → ENUM (order_type) ----
        op.execute(
            sa.text(
                f"ALTER TABLE {table} "
                f"ALTER COLUMN order_type TYPE order_type_enum "
                f"USING order_type::order_type_enum"
            )
        )

        # ---- 3. VARCHAR → ENUM (order_side) ----
        op.execute(
            sa.text(
                f"ALTER TABLE {table} "
                f"ALTER COLUMN order_side TYPE order_side_enum "
                f"USING order_side::order_side_enum"
            )
        )

    # Postgres doesn’t drop enums automatically; clean up
    op.execute(sa.text("DROP TYPE order_type_enum"))
    op.execute(sa.text("DROP TYPE order_side_enum"))
