from pybinbot import timestamp
from sqlmodel import SQLModel, Field, Column, JSON
from uuid import uuid4, UUID


class InquiryTable(SQLModel, table=True):
    id: UUID = Field(
        default_factory=uuid4, primary_key=True, index=True, nullable=False, unique=True
    )
    full_name: str = Field(nullable=False, max_length=256, min_length=1)
    email: str = Field(nullable=False, max_length=256, min_length=1)
    phone: str | None = Field(default=None, max_length=32, nullable=True)
    organisation: str | None = Field(default=None, max_length=256, nullable=True)
    reason: str | None = Field(default=None, max_length=256, nullable=True)
    message: str | None = Field(default=None, sa_column=Column(JSON))
    newsletter: bool = Field(default=False)
    terms_agreement: bool = Field(default=True)
    created_at: float = Field(default_factory=timestamp)
    updated_at: float = Field(default_factory=timestamp)
