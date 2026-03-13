"""Inquiries table

Revision ID: 9a40b3d1f7a0
Revises: f5152a7a008b
Create Date: 2026-03-13 22:41:06.127792

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9a40b3d1f7a0"
down_revision: Union[str, Sequence[str], None] = "f5152a7a008b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "inquirytable",
        sa.Column(
            "id", sa.UUID(as_uuid=True), primary_key=True, nullable=False, unique=True
        ),
        sa.Column("full_name", sa.String(length=256), nullable=False),
        sa.Column("email", sa.String(length=256), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("organisation", sa.String(length=256), nullable=True),
        sa.Column("reason", sa.String(length=256), nullable=True),
        sa.Column("message", sa.JSON(), nullable=True),
        sa.Column(
            "newsletter", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column(
            "terms_agreement",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column("created_at", sa.Float(), nullable=False),
        sa.Column("updated_at", sa.Float(), nullable=False),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("inquirytable")
