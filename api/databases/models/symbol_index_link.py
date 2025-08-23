from sqlmodel import SQLModel, Field


class SymbolIndexLink(SQLModel, table=True):
    symbol_id: str = Field(foreign_key="symbol.id", primary_key=True)
    asset_index_id: str = Field(foreign_key="asset_index.id", primary_key=True)
