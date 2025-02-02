from fastapi import APIRouter
from database.symbols_crud import SymbolsCrud
from symbols.models import SymbolsResponse, GetOneSymbolResponse
from apis import BinanceApi
from tools.exceptions import BinbotErrors

research_blueprint = APIRouter()


@research_blueprint.post(
    "/blacklist", response_model=GetOneSymbolResponse, tags=["Symbols"]
)
def post_blacklist(symbol: str, reason: str = ""):
    """
    Create a new Blacklist pair item.
    """
    data = SymbolsCrud().add_symbol(symbol=symbol, reason=reason, active=True)
    return GetOneSymbolResponse(message="Symbols found!", data=data)


@research_blueprint.delete(
    "/blacklist/{pair}", response_model=GetOneSymbolResponse, tags=["Symbols"]
)
def delete_symbol(pair: str):
    """
    Given symbol/pair, delete an already blacklisted item
    """
    data = SymbolsCrud().delete_symbol(pair)
    return GetOneSymbolResponse(message="Symbol deleted", data=data)


@research_blueprint.put(
    "/blacklist", response_model=GetOneSymbolResponse, tags=["Symbols"]
)
def edit_symbol(symbol, active: bool = True, reason: str = ""):
    """
    Modify a blacklisted item
    """
    data = SymbolsCrud().edit_symbol_item(symbol=symbol, active=active, reason=reason)
    return GetOneSymbolResponse(message="Symbol edited", data=data)


@research_blueprint.get("/blacklist", response_model=SymbolsResponse, tags=["Symbols"])
def get_blacklisted_symbols():
    """
    Get all symbols/pairs blacklisted
    """
    data = SymbolsCrud().get_all(active=False)
    return SymbolsResponse(message="Successfully retrieved blacklist", data=data)


@research_blueprint.get("/store-symbols", tags=["Symbols"])
def store_symbols():
    """
    Store all symbols from Binance
    """
    b_api = BinanceApi()
    data = b_api.ticker(json=False)
    symbol_controller = SymbolsCrud()

    for item in data:
        try:
            symbol = symbol_controller.get_symbol(item["symbol"])
        except BinbotErrors:
            symbol = None
            pass

        if item["symbol"].endswith("USDC") and not symbol:
            symbol_controller.add_symbol(item["symbol"])

    return GetOneSymbolResponse(message="Symbols stored!")


@research_blueprint.get("/blacklist", response_model=SymbolsResponse, tags=["Symbols"])
def get_all_symbols():
    """
    Get all active/not blacklisted symbols/pairs
    """
    data = SymbolsCrud().get_all(active=True)
    return SymbolsResponse(message="Successfully retrieved blacklist", data=data)
