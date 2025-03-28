"""alter margin_repay_id column to support Big integers (Binance ID is that size)

Revision ID: 61e207bcf0e0
Revises: b03fb01cc24f
Create Date: 2025-03-13 00:23:44.687719

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "61e207bcf0e0"
down_revision: Union[str, None] = "b03fb01cc24f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column(
        "deal",
        "margin_repay_id",
        existing_type=sa.INTEGER(),
        type_=sa.BigInteger(),
        nullable=True,
    )
    op.drop_column("paper_trading", "total_commission")
    op.create_unique_constraint(None, "test_autotrade", ["id"])
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column(
        "deal",
        "margin_repay_id",
        existing_type=sa.BigInteger(),
        type_=sa.INTEGER(),
        nullable=False,
    )
