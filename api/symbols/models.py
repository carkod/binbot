from typing import Optional, Sequence
from tools.handle_error import StandardResponse
from databases.models.symbol_table import SymbolTable
from pydantic import Field, BaseModel


class SymbolsResponse(StandardResponse):
    data: Sequence[SymbolTable] = Field(default=[])

    model_config = {"from_attributes": True}

    @classmethod
    def dump_from_table(cls, symbols: Sequence[SymbolTable]):
        """
        Same as model_dump() but from
        BotTable

        Use model_validate to cast/pre-validate data to avoid unecessary validation errors
        """
        new_data = []
        for s in symbols:
            symbol = s.model_dump()
            symbol["asset_indices"] = []
            if len(s.asset_indices) > 0:
                for asset in s.asset_indices:
                    symbol["asset_indices"].append(asset.model_dump())

            new_data.append(symbol)

        return new_data


class GetOneSymbolResponse(StandardResponse):
    data: Optional[SymbolTable] = Field(default=None)


class SymbolPayload(BaseModel):
    id: str
    blacklist_reason: str = ""
    active: bool = True
    cooldown: int = 0
    cooldown_start_ts: int = 0
