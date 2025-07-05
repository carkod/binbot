"""create_staging_balance_tables

Revision ID: 5f14b93b6741
Revises: 46c739c73ec3
Create Date: 2025-07-05 23:13:59.092238

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "5f14b93b6741"
down_revision: Union[str, None] = "46c739c73ec3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Check if tables already exist (in case SQLModel created them)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()

    if "staging_consolidated_balances" not in existing_tables:
        # Create staging_consolidated_balances table
        op.create_table(
            "staging_consolidated_balances",
            sa.Column("id", sa.BigInteger(), nullable=False),
            sa.Column("estimated_total_fiat", sa.Float(), nullable=False, default=0),
            sa.PrimaryKeyConstraint("id"),
            sa.Index(op.f("ix_staging_consolidated_balances_id"), "id"),
        )

    if "staging_balances" not in existing_tables:
        # Create staging_balances table
        op.create_table(
            "staging_balances",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("timestamp", sa.BigInteger(), nullable=False),
            sa.Column("asset", sa.String(), nullable=False),
            sa.Column("quantity", sa.Float(), nullable=True, default=0),
            sa.Column("consolidated_balances_id", sa.BigInteger(), nullable=True),
            sa.ForeignKeyConstraint(
                ["consolidated_balances_id"],
                ["staging_consolidated_balances.id"],
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.Index(op.f("ix_staging_balances_id"), "id"),
            sa.Index(op.f("ix_staging_balances_timestamp"), "timestamp"),
            sa.Index(op.f("ix_staging_balances_asset"), "asset"),
        )


def downgrade() -> None:
    # Drop tables in reverse order due to foreign key constraints
    op.drop_table("staging_balances")
    op.drop_table("staging_consolidated_balances")
