from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field as PydanticField
from sqlalchemy import BigInteger, Column, DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel


JsonVariant = JSON().with_variant(JSONB(), "postgresql")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Web3CandidateBase(BaseModel):
    source: str = PydanticField(..., max_length=50)
    project_name: str
    symbol: str | None = PydanticField(default=None, max_length=32)
    announcement_url: str | None = None
    announcement_title: str | None = None
    announced_at: datetime | None = None
    event_start_at: datetime | None = None
    event_end_at: datetime | None = None
    expected_listing_at: datetime | None = None
    chain: str | None = PydanticField(default=None, max_length=50)
    contract_address: str | None = None
    status: str = PydanticField(default="discovered", max_length=32)
    raw_payload: dict[str, Any] | None = None


class Web3CandidateCreate(Web3CandidateBase):
    pass


class Web3CandidateUpdate(BaseModel):
    source: str | None = PydanticField(default=None, max_length=50)
    project_name: str | None = None
    symbol: str | None = PydanticField(default=None, max_length=32)
    announcement_url: str | None = None
    announcement_title: str | None = None
    announced_at: datetime | None = None
    event_start_at: datetime | None = None
    event_end_at: datetime | None = None
    expected_listing_at: datetime | None = None
    chain: str | None = PydanticField(default=None, max_length=50)
    contract_address: str | None = None
    status: str | None = PydanticField(default=None, max_length=32)
    raw_payload: dict[str, Any] | None = None


class Web3CandidateTable(SQLModel, table=True):
    __tablename__ = "web3_candidates"

    id: int | None = Field(
        default=None,
        sa_column=Column(
            BigInteger().with_variant(Integer, "sqlite"),
            primary_key=True,
            autoincrement=True,
        ),
    )
    source: str = Field(nullable=False, max_length=50, index=True)
    project_name: str = Field(sa_column=Column(Text, nullable=False))
    symbol: str | None = Field(default=None, max_length=32, index=True)
    announcement_url: str | None = Field(default=None, sa_column=Column(Text))
    announcement_title: str | None = Field(default=None, sa_column=Column(Text))
    announced_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
    )
    event_start_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
    )
    event_end_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
    )
    expected_listing_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
    )
    chain: str | None = Field(default=None, max_length=50, index=True)
    contract_address: str | None = Field(default=None, sa_column=Column(Text))
    status: str = Field(
        default="discovered",
        sa_column=Column(
            String(32),
            nullable=False,
            server_default="discovered",
            index=True,
        ),
    )
    raw_payload: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JsonVariant),
    )
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
        ),
    )
    updated_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
            onupdate=func.now(),
        ),
    )
