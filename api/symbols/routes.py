from fastapi import APIRouter, Depends
from database.symbols_crud import SymbolsCrud
from symbols.models import SymbolsResponse, GetOneSymbolResponse
from database.utils import get_session
from sqlmodel import Session
from tools.handle_error import StandardResponse, BinbotErrors

research_blueprint = APIRouter()


@research_blueprint.get("/", response_model=SymbolsResponse, tags=["Symbols"])
def get_all_symbols(session: Session = Depends(get_session)):
    """
    Get all active/not blacklisted symbols/pairs
    """
    data = SymbolsCrud(session=session).get_all(active=True)
    return SymbolsResponse(message="Successfully retrieved blacklist", data=data)


@research_blueprint.post("/", response_model=GetOneSymbolResponse, tags=["Symbols"])
def add_symbol(
    symbol: str,
    reason: str = "",
    active: bool = True,
    session: Session = Depends(get_session),
):
    """
    Create a new symbol/pair.

    If active=False, the pair is blacklisted
    """
    data = SymbolsCrud(session=session).add_symbol(
        symbol=symbol, reason=reason, active=active
    )
    return GetOneSymbolResponse(message="Symbols found!", data=data)


@research_blueprint.delete(
    "/{pair}", response_model=GetOneSymbolResponse, tags=["Symbols"]
)
def delete_symbol(pair: str, session: Session = Depends(get_session)):
    """
    Given symbol/pair, delete a symbol

    Should not be used often. If need to blacklist, simply
    set active=False
    """
    data = SymbolsCrud(session=session).delete_symbol(pair)
    return GetOneSymbolResponse(message="Symbol deleted", data=data)


@research_blueprint.put("/", response_model=GetOneSymbolResponse, tags=["Symbols"])
def edit_symbol(
    symbol,
    active: bool = True,
    reason: str = "",
    session: Session = Depends(get_session),
):
    """
    Modify a blacklisted item
    """
    data = SymbolsCrud(session=session).edit_symbol_item(
        symbol=symbol, active=active, reason=reason
    )
    return GetOneSymbolResponse(message="Symbol edited", data=data)


@research_blueprint.get("/blacklist", response_model=SymbolsResponse, tags=["Symbols"])
def get_blacklisted_symbols(session: Session = Depends(get_session)):
    """
    Get all symbols/pairs blacklisted
    """
    data = SymbolsCrud(session=session).get_all(active=False)
    return SymbolsResponse(message="Successfully retrieved blacklist", data=data)


@research_blueprint.get("/store", tags=["Symbols"])
def store_symbols(session: Session = Depends(get_session)):
    """
    Store all symbols from Binance
    """
    try:
        SymbolsCrud(session=session).refresh_symbols_table()
        return GetOneSymbolResponse(message="Symbols stored!")
    except BinbotErrors as e:
        return StandardResponse(message=str(e), error=1)
