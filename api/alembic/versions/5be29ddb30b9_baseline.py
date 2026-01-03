"""baseline

Revision ID: 5be29ddb30b9
Revises:
Create Date: 2025-12-10 13:53:32.736162

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "5be29ddb30b9"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
