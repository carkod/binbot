from sqlmodel import SQLModel, Field
from database.utils import timestamp
from sqlalchemy import BigInteger, Column


class SymbolTable(SQLModel, table=True):
    __tablename__ = "symbol"

    id: str = Field(primary_key=True, description="Symbol")
    created_at: int = Field(
        default_factory=timestamp, sa_column=Column(BigInteger, nullable=False)
    )
    updated_at: int = Field(
        default_factory=timestamp, sa_column=Column(BigInteger, nullable=False)
    )
    active: bool = Field(default=True, description="Blacklisted items = false")
    blacklist_reason: str = Field(default="")
