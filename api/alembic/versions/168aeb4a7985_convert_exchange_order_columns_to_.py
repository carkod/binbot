"""convert_exchange_order_columns_to_varchar

Revision ID: 168aeb4a7985
Revises:
Create Date: 2025-12-10 00:25:45.947142

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "168aeb4a7985"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()

    # Add USDT to quoteassets enum if it doesn't exist (only for PostgreSQL)
    if conn.dialect.name == "postgresql":
        try:
            op.execute("ALTER TYPE quoteassets ADD VALUE IF NOT EXISTS 'USDT'")
        except Exception:
            pass  # Enum might not exist yet or already has the value

    # Check if migration already ran by looking for order_id_temp column
    result = conn.execute(
        sa.text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='exchange_order' AND column_name='order_id_temp'"
        )
    ).fetchone()

    if result:
        # Migration already in progress or completed
        return

    # Check if exchange_order table exists and has order_id column
    table_check = conn.execute(
        sa.text(
            "SELECT column_name, data_type FROM information_schema.columns "
            "WHERE table_name='exchange_order' AND column_name='order_id'"
        )
    ).fetchone()

    if not table_check:
        # Table doesn't exist or order_id column doesn't exist
        return

    # Check if already VARCHAR
    if table_check[1].upper() in ("CHARACTER VARYING", "VARCHAR", "TEXT"):
        # Already migrated
        return

    # Run the migration for exchange_order
    op.add_column(
        "exchange_order", sa.Column("order_id_temp", sa.String(), nullable=True)
    )
    op.execute(
        sa.text("UPDATE exchange_order SET order_id_temp = CAST(order_id AS VARCHAR)")
    )
    op.drop_column("exchange_order", "order_id")
    op.alter_column("exchange_order", "order_id_temp", new_column_name="order_id")
    op.alter_column("exchange_order", "order_id", nullable=False)
    op.execute(
        sa.text(
            "ALTER TABLE exchange_order ALTER COLUMN order_type TYPE VARCHAR USING order_type::VARCHAR"
        )
    )
    op.execute(
        sa.text(
            "ALTER TABLE exchange_order ALTER COLUMN order_side TYPE VARCHAR USING order_side::VARCHAR"
        )
    )

    # Do the same for fake_order table if it exists
    fake_check = conn.execute(
        sa.text(
            "SELECT column_name, data_type FROM information_schema.columns "
            "WHERE table_name='fake_order' AND column_name='order_id'"
        )
    ).fetchone()

    if fake_check and fake_check[1].upper() not in (
        "CHARACTER VARYING",
        "VARCHAR",
        "TEXT",
    ):
        op.add_column(
            "fake_order", sa.Column("order_id_temp", sa.String(), nullable=True)
        )
        op.execute(
            sa.text("UPDATE fake_order SET order_id_temp = CAST(order_id AS VARCHAR)")
        )
        op.drop_column("fake_order", "order_id")
        op.alter_column("fake_order", "order_id_temp", new_column_name="order_id")
        op.alter_column("fake_order", "order_id", nullable=False)
        op.execute(
            sa.text(
                "ALTER TABLE fake_order ALTER COLUMN order_type TYPE VARCHAR USING order_type::VARCHAR"
            )
        )
        op.execute(
            sa.text(
                "ALTER TABLE fake_order ALTER COLUMN order_side TYPE VARCHAR USING order_side::VARCHAR"
            )
        )


def downgrade() -> None:
    """Downgrade schema."""
    # Reverse the changes for fake_order
    op.execute(
        "ALTER TABLE fake_order ALTER COLUMN order_side TYPE VARCHAR"
    )  # Keep as VARCHAR, reverse not fully supported
    op.execute("ALTER TABLE fake_order ALTER COLUMN order_type TYPE VARCHAR")
    op.add_column(
        "fake_order", sa.Column("order_id_temp", sa.BigInteger(), nullable=True)
    )
    op.execute("UPDATE fake_order SET order_id_temp = CAST(order_id AS BIGINT)")
    op.drop_column("fake_order", "order_id")
    op.alter_column("fake_order", "order_id_temp", new_column_name="order_id")
    op.alter_column("fake_order", "order_id", nullable=False)

    # Reverse the changes for exchange_order
    op.execute("ALTER TABLE exchange_order ALTER COLUMN order_side TYPE VARCHAR")
    op.execute("ALTER TABLE exchange_order ALTER COLUMN order_type TYPE VARCHAR")
    op.add_column(
        "exchange_order", sa.Column("order_id_temp", sa.BigInteger(), nullable=True)
    )
    op.execute("UPDATE exchange_order SET order_id_temp = CAST(order_id AS BIGINT)")
    op.drop_column("exchange_order", "order_id")
    op.alter_column("exchange_order", "order_id_temp", new_column_name="order_id")
    op.alter_column("exchange_order", "order_id", nullable=False)
