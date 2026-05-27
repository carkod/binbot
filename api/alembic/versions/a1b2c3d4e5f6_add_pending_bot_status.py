"""add pending bot status

Revision ID: a1b2c3d4e5f6
Revises: e2f3a4b5c6d7
Create Date: 2026-05-26 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "e2f3a4b5c6d7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE status ADD VALUE IF NOT EXISTS 'pending'")


def downgrade() -> None:
    op.execute(
        "CREATE TYPE status_old AS ENUM ('all','inactive','active','completed','error')"
    )
    op.execute(
        "ALTER TABLE bot ALTER COLUMN status TYPE status_old USING status::text::status_old"
    )
    op.execute(
        "ALTER TABLE paper_trading ALTER COLUMN status TYPE status_old USING status::text::status_old"
    )
    op.execute("DROP TYPE status")
    op.execute("ALTER TYPE status_old RENAME TO status")
