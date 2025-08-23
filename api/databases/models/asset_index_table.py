from sqlmodel import SQLModel, Field, Relationship
from typing import TYPE_CHECKING
from sqlalchemy import Column, String, ForeignKey


if TYPE_CHECKING:
    from databases.models.symbol_table import SymbolTable


class SymbolIndexLink(SQLModel, table=True):
    symbol_id: str = Field(
        sa_column=Column(
            String, ForeignKey("symbol.id", ondelete="CASCADE"), primary_key=True
        )
    )
    asset_index_id: str = Field(
        sa_column=Column(
            String, ForeignKey("asset_index.id", ondelete="CASCADE"), primary_key=True
        )
    )


class AssetIndexTable(SQLModel, table=True):
    __tablename__ = "asset_index"

    id: str = Field(primary_key=True, description="Unique ID")
    name: str = Field(default="", description="Name of the index")

    symbols: list["SymbolTable"] = Relationship(
        back_populates="asset_indices",
        link_model=SymbolIndexLink,
        sa_relationship_kwargs={
            "lazy": "joined",
            "single_parent": True,
            "cascade": "all, delete, delete-orphan",
        },
    )
