from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlmodel import Session

from databases.crud.web3_candidates import Web3CandidatesCrud
from databases.utils import get_session
from databases.web3_candidates import Web3CandidateCreate
from user.models.user import UserTokenData
from user.services.auth import get_current_user
from web3_candidates.models import Web3CandidateListResponse, Web3CandidateResponse


web3_candidates_blueprint = APIRouter(
    prefix="/web3/candidates",
    tags=["web3-candidates"],
)


@web3_candidates_blueprint.post("", response_model=Web3CandidateResponse)
def create_web3_candidate(
    payload: Web3CandidateCreate,
    session: Session = Depends(get_session),
    _: UserTokenData = Depends(get_current_user),
):
    row = Web3CandidatesCrud(session).create(payload)
    return {
        "message": "Web3 candidate created",
        "data": row,
        "error": 0,
    }


@web3_candidates_blueprint.get("", response_model=Web3CandidateListResponse)
def list_web3_candidates(
    source: str | None = Query(default=None),
    status: str | None = Query(default=None),
    symbol: str | None = Query(default=None),
    chain: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_session),
    _: UserTokenData = Depends(get_current_user),
):
    rows = Web3CandidatesCrud(session).list(
        source=source,
        status=status,
        symbol=symbol,
        chain=chain,
        limit=limit,
        offset=offset,
    )
    return {
        "message": "Web3 candidates retrieved",
        "data": rows,
        "error": 0,
    }


@web3_candidates_blueprint.get("/{candidate_id}", response_model=Web3CandidateResponse)
def get_web3_candidate(
    candidate_id: int,
    session: Session = Depends(get_session),
    _: UserTokenData = Depends(get_current_user),
):
    row = Web3CandidatesCrud(session).get(candidate_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Web3 candidate not found")
    return {
        "message": "Web3 candidate retrieved",
        "data": row,
        "error": 0,
    }


@web3_candidates_blueprint.delete("")
def delete_web3_candidate(
    id: int = Query(..., description="Web3 candidate id to delete"),
    session: Session = Depends(get_session),
    _: UserTokenData = Depends(get_current_user),
):
    row = Web3CandidatesCrud(session).delete(id)
    if row is None:
        raise HTTPException(status_code=404, detail="Web3 candidate not found")
    return Response(status_code=204)


@web3_candidates_blueprint.delete("/{candidate_id}")
def delete_web3_candidate_by_path(
    candidate_id: int,
    session: Session = Depends(get_session),
    _: UserTokenData = Depends(get_current_user),
):
    row = Web3CandidatesCrud(session).delete(candidate_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Web3 candidate not found")
    return Response(status_code=204)
