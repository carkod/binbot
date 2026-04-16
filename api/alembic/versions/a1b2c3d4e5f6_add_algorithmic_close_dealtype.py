"""Add algorithmic_close to DealType enum

Revision ID: a1b2c3d4e5f6
Revises: 4a7f42d3c1ab
Create Date: 2026-04-15 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "4a7f42d3c1ab"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TYPE dealtype ADD VALUE IF NOT EXISTS 'algorithmic_close'")


def downgrade() -> None:
    """Downgrade schema."""
    # PostgreSQL does not support removing enum values directly.
    # To downgrade, recreate the enum type without 'algorithmic_close'.
    op.execute(
        "UPDATE exchange_order SET deal_type = 'panic_close' "
        "WHERE deal_type = 'algorithmic_close'"
    )
    op.execute(
        "UPDATE fake_order SET deal_type = 'panic_close' "
        "WHERE deal_type = 'algorithmic_close'"
    )
    op.execute(
        "CREATE TYPE dealtype_new AS ENUM ("
        "'base_order', 'take_profit', 'stop_loss', 'short_sell', "
        "'short_buy', 'margin_short', 'panic_close', 'trailling_profit', 'conversion'"
        # Note: 'trailling_profit' (old spelling) is intentional here - at the point
        # when this migration is being downgraded, migration b2c3d4e5f6a7 will have
        # already been downgraded first, reverting the column value back to 'trailling_profit'.
        ")"
    )
    op.execute(
        "ALTER TABLE exchange_order "
        "ALTER COLUMN deal_type TYPE dealtype_new "
        "USING deal_type::text::dealtype_new"
    )
    op.execute(
        "ALTER TABLE fake_order "
        "ALTER COLUMN deal_type TYPE dealtype_new "
        "USING deal_type::text::dealtype_new"
    )
    op.execute("DROP TYPE dealtype")
    op.execute("ALTER TYPE dealtype_new RENAME TO dealtype")
