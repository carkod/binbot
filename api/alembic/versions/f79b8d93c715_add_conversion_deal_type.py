"""add conversion deal type

Revision ID: f79b8d93c715
Revises: 49859b6aac65
Create Date: 2025-09-04 20:21:35.211165

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "f79b8d93c715"
down_revision: Union[str, None] = "49859b6aac65"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add 'conversion' to dealtype enum
    op.execute("ALTER TYPE dealtype ADD VALUE IF NOT EXISTS 'conversion';")


def downgrade() -> None:
    # Remove 'conversion' from dealtype enum (PostgreSQL workaround)
    op.execute(
        "UPDATE exchange_order SET deal_type = 'base_order' WHERE deal_type = 'conversion';"
    )
    op.execute(
        "CREATE TYPE dealtype_new AS ENUM ('base_order', 'take_profit', 'stop_loss', 'short_sell', 'short_buy', 'margin_short', 'panic_close', 'trailling_profit');"
    )
    op.execute(
        "ALTER TABLE exchange_order ALTER COLUMN deal_type TYPE dealtype_new USING deal_type::text::dealtype_new;"
    )
    op.execute("DROP TYPE dealtype;")
    op.execute("ALTER TYPE dealtype_new RENAME TO dealtype;")
