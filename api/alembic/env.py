from alembic import context
from database.api_db import db_url
from database.models.user_table import UserTable # noqa
from database.models.order_table import ExchangeOrderTable # noqa
from sqlmodel import SQLModel


def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    context.configure(
        url=db_url,
        target_metadata=SQLModel.metadata,
        literal_binds=True,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


run_migrations_offline()
