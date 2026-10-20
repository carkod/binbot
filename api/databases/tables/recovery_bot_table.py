from typing import Optional
from uuid import UUID, uuid4

from pybinbot import timestamp
from sqlalchemy import Column, ForeignKey, Uuid
from sqlmodel import Field, SQLModel


class RecoveryBotTable(SQLModel, table=True):
    __tablename__ = "recovery_bot_table"

    id: Optional[UUID] = Field(
        default_factory=uuid4, primary_key=True, index=True, nullable=False, unique=True
    )
    reversal_path: str = Field(default="source")
    source_contracts: float = Field(default=0)
    source_loss_fiat: float = Field(default=0)
    stop_loss_pct: float = Field(default=0)
    source_bot_id: UUID | None = Field(
        default=None,
        sa_column=Column(
            Uuid(),
            ForeignKey(
                "bot.id",
                name="fk_recovery_source_bot",
                ondelete="SET NULL",
                use_alter=True,
            ),
            unique=True,
            index=True,
            nullable=True,
        ),
    )
    source_close_order_id: str | None = None
    created_at: float = Field(default_factory=timestamp)
    updated_at: float = Field(default_factory=timestamp)
