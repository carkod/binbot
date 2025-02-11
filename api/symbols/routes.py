from fastapi import APIRouter, Depends
from database.symbols_crud import SymbolsCrud
from symbols.models import SymbolsResponse, GetOneSymbolResponse
from database.utils import get_session
from sqlmodel import Session
from tools.handle_error import StandardResponse, BinbotErrors
from symbols.models import SymbolPayload
from typing import Optional

symbols_blueprint = APIRouter()


@symbols_blueprint.get("/symbol", response_model=SymbolsResponse, tags=["Symbols"])
def get_all_symbols(active: Optional[bool] = None, session: Session = Depends(get_session)):
    """
    Get all symbols/pairs

    Args:
    - Active: includes symbols set as True and also cooldown delta is negative
    """
    data = SymbolsCrud(session=session).get_all(active=active)
    return SymbolsResponse(message="Successfully retrieved blacklist", data=data)


@symbols_blueprint.post(
    "/symbol", response_model=GetOneSymbolResponse, tags=["Symbols"]
)
def add_symbol(
    symbol: str,
    quote_asset: str,
    base_asset: str,
    min_notional: float = 0,
    price_precision: int = 0,
    qty_precision: int = 0,
    reason: str = "",
    active: bool = True,
    session: Session = Depends(get_session),
):
    """
    Create a new symbol/pair.

    If active=False, the pair is blacklisted
    """
    data = SymbolsCrud(session=session).add_symbol(
        symbol=symbol,
        reason=reason,
        active=active,
        quote_asset=quote_asset,
        base_asset=base_asset,
        min_notional=min_notional,
        price_precision=price_precision,
        qty_precision=qty_precision,
    )
    return GetOneSymbolResponse(message="Symbols found!", data=data)


@symbols_blueprint.delete(
    "/symbol/{pair}", response_model=GetOneSymbolResponse, tags=["Symbols"]
)
def delete_symbol(pair: str, session: Session = Depends(get_session)):
    """
    Given symbol/pair, delete a symbol

    Should not be used often. Newly created symbols should
    come from exchange. So deleting one requires
    refreshing_symbols_table in the future, as all the
    precision fields need to be updated.

    If need to blacklist, simply
    set active=False
    """
    data = SymbolsCrud(session=session).delete_symbol(pair)
    return GetOneSymbolResponse(message="Symbol deleted", data=data)


@symbols_blueprint.put("/symbol", response_model=GetOneSymbolResponse, tags=["Symbols"])
def edit_symbol(
    data: SymbolPayload,
    session: Session = Depends(get_session),
):
    """
    Modify a blacklisted item
    """
    data = SymbolsCrud(session=session).edit_symbol_item(data)
    return GetOneSymbolResponse(message="Symbol edited", data=data)


@symbols_blueprint.get("/blacklist", response_model=SymbolsResponse, tags=["Symbols"])
def get_blacklisted_symbols(session: Session = Depends(get_session)):
    """
    Get all symbols/pairs blacklisted
    """
    data = SymbolsCrud(session=session).get_all(active=False)
    return SymbolsResponse(message="Successfully retrieved blacklist", data=data)


@symbols_blueprint.get("/store", tags=["Symbols"])
def store_symbols(session: Session = Depends(get_session)):
    """
    Store all symbols from Binance
    """
    try:
        SymbolsCrud(session=session).refresh_symbols_table()
        return GetOneSymbolResponse(message="Symbols stored!")
    except BinbotErrors as e:
        return StandardResponse(message=str(e), error=1)
