from sqlmodel import SQLModel, Field
from database.utils import timestamp


class Blacklist(SQLModel, table=True):
    __tablename__ = "blacklist"

    id: int = Field(primary_key=True, description="Symbol")
    reason: str = Field(nullable=False)
    created_at: int = Field(default_factory=timestamp)
    updated_at: int = Field(default_factory=timestamp)
