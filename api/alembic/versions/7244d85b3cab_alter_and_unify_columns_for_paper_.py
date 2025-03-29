"""alter and unify columns for paper trading table

Revision ID: 7244d85b3cab
Revises: 61e207bcf0e0
Create Date: 2025-03-28 04:38:52.858363

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7244d85b3cab"
down_revision: Union[str, None] = "61e207bcf0e0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint(
        "paper_trading_deal_id_fkey", "paper_trading", type_="foreignkey"
    )
    op.create_foreign_key(
        None, "paper_trading", "deal", ["deal_id"], ["id"], ondelete="CASCADE"
    )
    op.drop_column("paper_trading", "short_buy_price")
    op.drop_column("paper_trading", "short_sell_price")
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "paper_trading",
        sa.Column(
            "short_sell_price",
            sa.DOUBLE_PRECISION(precision=53),
            autoincrement=False,
            nullable=False,
        ),
    )
    op.add_column(
        "paper_trading",
        sa.Column(
            "short_buy_price",
            sa.DOUBLE_PRECISION(precision=53),
            autoincrement=False,
            nullable=False,
        ),
    )
    op.create_foreign_key(
        "paper_trading_deal_id_fkey", "paper_trading", "deal", ["deal_id"], ["id"]
    )
    op.add_column(
        "autotrade",
        sa.Column("balance_to_use", sa.VARCHAR(), autoincrement=False, nullable=False),
    )
    # ### end Alembic commands ###
