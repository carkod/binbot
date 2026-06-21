"""add web3 candidates table

Revision ID: b6c7d8e9f0a1
Revises: a3b4c5d6e7f8
Create Date: 2026-06-21 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "b6c7d8e9f0a1"
down_revision: Union[str, Sequence[str], None] = "a3b4c5d6e7f8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "web3_candidates",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("project_name", sa.Text(), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=True),
        sa.Column("announcement_url", sa.Text(), nullable=True),
        sa.Column("announcement_title", sa.Text(), nullable=True),
        sa.Column("announced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("event_start_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("event_end_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expected_listing_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("chain", sa.String(length=50), nullable=True),
        sa.Column("contract_address", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=32),
            server_default="discovered",
            nullable=False,
        ),
        sa.Column(
            "raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_web3_candidates_source",
        "web3_candidates",
        ["source"],
        unique=False,
    )
    op.create_index(
        "ix_web3_candidates_symbol",
        "web3_candidates",
        ["symbol"],
        unique=False,
    )
    op.create_index(
        "ix_web3_candidates_chain",
        "web3_candidates",
        ["chain"],
        unique=False,
    )
    op.create_index(
        "ix_web3_candidates_status",
        "web3_candidates",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_web3_candidates_status", table_name="web3_candidates")
    op.drop_index("ix_web3_candidates_chain", table_name="web3_candidates")
    op.drop_index("ix_web3_candidates_symbol", table_name="web3_candidates")
    op.drop_index("ix_web3_candidates_source", table_name="web3_candidates")
    op.drop_table("web3_candidates")
