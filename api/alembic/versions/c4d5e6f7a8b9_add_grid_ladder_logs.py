"""add grid ladder logs

Revision ID: c4d5e6f7a8b9
Revises: b3c4d5e6f7a8
Create Date: 2026-05-24 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c4d5e6f7a8b9"
down_revision: Union[str, Sequence[str], None] = "b3c4d5e6f7a8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("grid_ladder", sa.Column("logs", sa.JSON(), nullable=True))
    op.execute("UPDATE grid_ladder SET logs = '[]' WHERE logs IS NULL")


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("grid_ladder", "logs")
