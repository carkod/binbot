"""Store recent futures prices from existing market ingests."""

import sqlalchemy as sa
from alembic import op

revision = "a0b1c2d3e4f5"
down_revision = "f6a81c2d490e"
branch_labels = None
depends_on = None

TABLE = "futures_price_sample"
UNIQUE = "uq_futures_price_sample_snapshot"
INDEX = "ix_futures_price_sample_source_recorded_at"


def upgrade() -> None:
    bind = op.get_bind()
    if not sa.inspect(bind).has_table(TABLE):
        op.create_table(
            TABLE,
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("source", sa.String(length=32), nullable=False),
            sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("symbol", sa.String(length=64), nullable=False),
            sa.Column("last_price", sa.Float(), nullable=False),
            sa.Column("price_change_percent", sa.Float(), nullable=False),
            sa.Column("turnover_24h", sa.Float(), nullable=False),
        )

    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns(TABLE)}
    for name, column_type in (
        ("source", sa.String(length=32)),
        ("recorded_at", sa.DateTime(timezone=True)),
        ("symbol", sa.String(length=64)),
        ("last_price", sa.Float()),
        ("price_change_percent", sa.Float()),
        ("turnover_24h", sa.Float()),
    ):
        if name not in columns:
            op.add_column(TABLE, sa.Column(name, column_type, nullable=True))

    inspector = sa.inspect(bind)
    constraints = {
        constraint["name"] for constraint in inspector.get_unique_constraints(TABLE)
    }
    if UNIQUE not in constraints:
        with op.batch_alter_table(TABLE) as batch:
            batch.create_unique_constraint(UNIQUE, ["source", "recorded_at", "symbol"])
    indexes = {index["name"] for index in sa.inspect(bind).get_indexes(TABLE)}
    if INDEX not in indexes:
        op.create_index(INDEX, TABLE, ["source", "recorded_at"])


def downgrade() -> None:
    if sa.inspect(op.get_bind()).has_table(TABLE):
        op.drop_table(TABLE)
