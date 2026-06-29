from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session
from api.databases.crud.signals_crud import SignalsCrud
from api.databases.utils import get_session
from api.signals.models import (
    SignalCreate,
    SignalListResponse,
    SignalResponse,
)
from api.user.models.user import UserTokenData
from api.user.services.auth import get_current_user
from api.databases.tables.signals_table import SignalsTable

signals_blueprint = APIRouter(tags=["signals"])


@signals_blueprint.post("/signals", response_model=SignalResponse)
def create_signal(
    payload: SignalCreate,
    session: Session = Depends(get_session),
    _: UserTokenData = Depends(get_current_user),
):
    crud = SignalsCrud(session)
    row = crud.create(**payload.model_dump())
    return {"message": "Signal recorded", "data": row, "error": 0}


@signals_blueprint.get("/signals", response_model=SignalListResponse)
def list_signals(
    algorithm_name: str | None = Query(default=None),
    symbol: str | None = Query(default=None),
    current_regime: str | None = Query(default=None),
    autotrade: bool | None = Query(default=None),
    since: datetime | None = Query(default=None),
    until: datetime | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    include_payload: bool = Query(default=True),
    session: Session = Depends(get_session),
    _: UserTokenData = Depends(get_current_user),
):
    crud = SignalsCrud(session)
    if include_payload:
        data = crud.query(
            algorithm_name=algorithm_name,
            symbol=symbol,
            current_regime=current_regime,
            autotrade=autotrade,
            since=since,
            until=until,
            limit=limit,
            offset=offset,
        )
        return {
            "message": "Signals retrieved",
            "data": data,
            "error": 0,
        }
    return {
        "message": "Signals retrieved",
        "data": crud.query_summary(
            algorithm_name=algorithm_name,
            symbol=symbol,
            current_regime=current_regime,
            autotrade=autotrade,
            since=since,
            until=until,
            limit=limit,
            offset=offset,
        ),
        "error": 0,
    }


@signals_blueprint.get("/signals/{signal_id}", response_model=SignalResponse)
def get_signal(
    signal_id: int,
    session: Session = Depends(get_session),
    _: UserTokenData = Depends(get_current_user),
):
    row = session.get(SignalsTable, signal_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Signal not found")
    return {"message": "Signal retrieved", "data": row, "error": 0}
