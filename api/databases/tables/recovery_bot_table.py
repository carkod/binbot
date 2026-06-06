from typing import Optional
from uuid import UUID, uuid4

from pybinbot import timestamp
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
    created_at: float = Field(default_factory=timestamp)
    updated_at: float = Field(default_factory=timestamp)
