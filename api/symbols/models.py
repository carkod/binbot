from typing import Optional, Sequence
from tools.handle_error import StandardResponse
from databases.models.symbol_table import SymbolTable
from pydantic import Field, BaseModel


class SymbolsResponse(StandardResponse):
    data: Sequence[SymbolTable] = Field(default=[])


class GetOneSymbolResponse(StandardResponse):
    data: Optional[SymbolTable] = Field(default=None)


class SymbolPayload(BaseModel):
    id: str
    blacklist_reason: str = ""
    active: bool = True
    cooldown: int = 0
    cooldown_start_ts: int = 0
