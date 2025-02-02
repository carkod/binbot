from typing import Optional, Sequence
from tools.handle_error import StandardResponse
from database.models.symbol_table import SymbolTable
from pydantic import Field


class SymbolsResponse(StandardResponse):
    data: Sequence[SymbolTable] = Field(default=[])


class GetOneSymbolResponse(StandardResponse):
    data: Optional[SymbolTable] = Field(default=None)
