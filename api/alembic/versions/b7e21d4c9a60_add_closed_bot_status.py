"""Retain failed conditional entries using the closed bot status."""

from alembic import op

revision = "b7e21d4c9a60"
down_revision = "f9c2a617d83e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE status ADD VALUE IF NOT EXISTS 'closed'")


def downgrade() -> None:
    # PostgreSQL cannot drop one enum value. Keep it so archived records retain
    # their meaning; downgrading must not delete them or make them tradable again.
    pass
