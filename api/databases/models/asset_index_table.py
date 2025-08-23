from sqlmodel import SQLModel, Field, Relationship
from typing import TYPE_CHECKING
from databases.models.symbol_index_link import SymbolIndexLink

if TYPE_CHECKING:
    from databases.models.symbol_table import SymbolTable


class AssetIndexTable(SQLModel, table=True):
    __tablename__ = "asset_index"

    id: str = Field(primary_key=True, description="Unique ID")
    name: str = Field(default="", description="Name of the index")

    symbols: list["SymbolTable"] = Relationship(
        back_populates="asset_indices",
        link_model=SymbolIndexLink,
        sa_relationship_kwargs={"lazy": "joined", "single_parent": True},
    )
