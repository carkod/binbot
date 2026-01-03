"""add enum value

Revision ID: 1ba34823c751
Revises: 5be29ddb30b9
Create Date: 2025-12-10 13:54:09.784427

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1ba34823c751"
down_revision: str | Sequence[str] | None = "5be29ddb30b9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TYPE quoteassets ADD VALUE IF NOT EXISTS 'USDT'")
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # Step 1: Create a new ENUM without the value
    op.execute("CREATE TYPE quoteassets_old AS ENUM ('BTC', 'ETH', 'EUR', 'etc')")

    # Step 2: ALTER each column that uses quoteassets
    op.execute("""
        ALTER TABLE your_table
        ALTER COLUMN your_column
        TYPE quoteassets_old
        USING your_column::text::quoteassets_old
    """)

    # Step 3: Drop the original enum
    op.execute("DROP TYPE quoteassets")

    # Step 4: Rename the old one back
    op.execute("ALTER TYPE quoteassets_old RENAME TO quoteassets")
