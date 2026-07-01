from datetime import datetime
from typing import Any
from sqlalchemy import Column, DateTime
from sqlmodel import SQLModel, Field
from api.tools.utils import JsonVariant


class SignalsTable(SQLModel, table=True):
    """
    Persisted record of every signal a strategy emits, regardless of whether
    autotrade fired. Stable join keys + decision in columns, evolving fields
    (regime context, indicators, strategy-specific params) in JSONB so adding
    a new strategy doesn't require schema changes.
    """

    __tablename__ = "signals"

    id: int | None = Field(default=None, primary_key=True)
    algorithm_name: str = Field(nullable=False, max_length=128, index=True)
    symbol: str = Field(nullable=False, max_length=64, index=True)
    generated_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False, index=True)
    )
    direction: str = Field(nullable=False, max_length=16)
    autotrade: bool = Field(default=False, nullable=False)
    current_regime: str | None = Field(default=None, max_length=32, index=True)

    # Schemaless payloads — strategies dump whatever they have. Postgres uses
    # JSONB (queryable + GIN-indexable); SQLite falls back to text JSON for tests.
    context: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JsonVariant))
    bot_params: dict[str, Any] = Field(
        default_factory=dict, sa_column=Column(JsonVariant)
    )
    indicators: dict[str, Any] = Field(
        default_factory=dict, sa_column=Column(JsonVariant)
    )
