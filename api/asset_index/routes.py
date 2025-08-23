from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session
from databases.utils import get_session
from databases.crud.asset_index_crud import AssetIndexCrud
from databases.models.asset_index_table import AssetIndexTable
from typing import List, Optional


asset_index_blueprint = APIRouter(tags=["asset-index"])


@asset_index_blueprint.get("/", response_model=List[AssetIndexTable])
def get_all_asset_indices(session: Session = Depends(get_session)):
    try:
        return AssetIndexCrud(session=session).get_all()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@asset_index_blueprint.get("/{index_id}", response_model=AssetIndexTable)
def get_asset_index(index_id: str, session: Session = Depends(get_session)):
    try:
        return AssetIndexCrud(session=session).get_index(index_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@asset_index_blueprint.post("/", response_model=AssetIndexTable)
def add_asset_index(id: str, name: str, session: Session = Depends(get_session)):
    try:
        return AssetIndexCrud(session=session).add_index(id=id, name=name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@asset_index_blueprint.put("/{index_id}", response_model=AssetIndexTable)
def edit_asset_index(
    index_id: str,
    name: Optional[str] = None,
    session: Session = Depends(get_session),
):
    try:
        return AssetIndexCrud(session=session).edit_index(index_id=index_id, name=name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@asset_index_blueprint.delete("/{index_id}", response_model=AssetIndexTable)
def delete_asset_index(index_id: str, session: Session = Depends(get_session)):
    try:
        return AssetIndexCrud(session=session).delete_index(index_id=index_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
