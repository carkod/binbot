"""
Add index field to symbol table

Revision ID: 2a7c1f0c1a3b
Revises: 5f14b93b6741
Create Date: 2025-08-11 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "2a7c1f0c1a3b"
# Updated to point to the latest head to resolve multiple heads
# Previously: down_revision = "f5681454997c"
down_revision: Union[str, None] = "5f14b93b6741"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new column `index` with empty string default for existing rows
    op.add_column(
        "symbol",
        sa.Column("index", sa.String(), nullable=False, server_default=""),
    )
    # Optionally drop the server_default to match application-level default only
    op.alter_column("symbol", "index", server_default=None)


def downgrade() -> None:
    # Drop the `index` column on downgrade
    op.drop_column("symbol", "index")
