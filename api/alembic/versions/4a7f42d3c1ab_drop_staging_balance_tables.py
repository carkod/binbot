"""Drop staging balance tables

Revision ID: 4a7f42d3c1ab
Revises: 9a40b3d1f7a0
Create Date: 2026-04-07 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "4a7f42d3c1ab"
down_revision: Union[str, Sequence[str], None] = "9a40b3d1f7a0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_table("staging_balances")
    op.drop_table("staging_consolidated_balances")


def downgrade() -> None:
    """Downgrade schema."""
    op.create_table(
        "staging_consolidated_balances",
        sa.Column("id", sa.BigInteger(), primary_key=True, nullable=False),
        sa.Column("estimated_total_fiat", sa.Float(), nullable=False),
    )
    op.create_index(
        "ix_staging_consolidated_balances_id",
        "staging_consolidated_balances",
        ["id"],
        unique=False,
    )

    op.create_table(
        "staging_balances",
        sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
        sa.Column("timestamp", sa.BigInteger(), nullable=False),
        sa.Column("asset", sa.String(), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=True),
        sa.Column("consolidated_balances_id", sa.BigInteger(), nullable=True),
        sa.ForeignKeyConstraint(
            ["consolidated_balances_id"],
            ["staging_consolidated_balances.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("id"),
    )
    op.create_index("ix_staging_balances_id", "staging_balances", ["id"], unique=False)
    op.create_index(
        "ix_staging_balances_timestamp",
        "staging_balances",
        ["timestamp"],
        unique=False,
    )
    op.create_index(
        "ix_staging_balances_asset",
        "staging_balances",
        ["asset"],
        unique=False,
    )
