"""Remove paper trading, simulated orders, and test autotrade settings.

Paper-only deal records are deleted before their ownership information is lost.
This data removal cannot be reversed; restore a backup to recover paper history.
"""

import sqlalchemy as sa
from alembic import op

revision = "d7e8f9a0b1c2"
down_revision = "a7b4e9c261f0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    # Drop children first, without CASCADE against unrelated schema objects.
    if "fake_order" in tables:
        op.drop_table("fake_order")

    if "paper_trading" in tables:
        if "deal" in tables and "deal_id" in {
            column["name"] for column in inspector.get_columns("paper_trading")
        }:
            paper = sa.table("paper_trading", sa.column("deal_id"))
            deal = sa.table("deal", sa.column("id"))
            paper_deals = (
                sa.select(paper.c.deal_id)
                .where(paper.c.deal_id.is_not(None))
                .distinct()
            )
            # Detach paper owners before deleting referenced deals. Keep the IDs
            # in memory so partially migrated schemas need no temporary table.
            deal_ids = list(bind.execute(paper_deals).scalars())
            bind.execute(paper.update().values(deal_id=None))
            for offset in range(0, len(deal_ids), 500):
                deletion = deal.delete().where(
                    deal.c.id.in_(deal_ids[offset : offset + 500])
                )
                if "bot" in tables:
                    bot = sa.table("bot", sa.column("deal_id"))
                    deletion = deletion.where(
                        ~sa.exists(sa.select(1).where(bot.c.deal_id == deal.c.id))
                    )
                bind.execute(deletion)
        op.drop_table("paper_trading")

    if "test_autotrade" in tables:
        op.drop_table("test_autotrade")


def downgrade() -> None:
    raise RuntimeError(
        "Paper trading removal is irreversible. Restore a database backup to recover it."
    )
