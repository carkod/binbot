"""alter margin_loan_id column to support Big integers

Revision ID: b03fb01cc24f
Revises: 113eb73ebba8
Create Date: 2025-03-10 03:22:34.011029

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b03fb01cc24f"
down_revision: Union[str, None] = "113eb73ebba8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "deal",
        "margin_loan_id",
        existing_type=sa.INTEGER(),
        type_=sa.BigInteger(),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "deal",
        "margin_loan_id",
        existing_type=sa.BigInteger(),
        type_=sa.INTEGER(),
        nullable=False,
    )
