from databases.utils import independent_session
from sqlmodel import Session, select
from databases.models.asset_index_table import AssetIndexTable
from typing import Optional, Sequence


class AssetIndexCrud:
    """
    Database operations for AssetIndexTable
    """

    def __init__(self, session: Session | None = None):
        if session is None:
            session = independent_session()
        self.session = session

    def get_all(self) -> Sequence[AssetIndexTable]:
        statement = select(AssetIndexTable)
        results = self.session.exec(statement).unique().all()
        self.session.close()
        return results

    def get_index(self, index_id: str) -> AssetIndexTable:
        statement = select(AssetIndexTable).where(AssetIndexTable.id == index_id)
        result = self.session.exec(statement).first()
        if result:
            self.session.close()
            return result
        else:
            raise ValueError("Asset index not found")

    def add_index(self, id: str, name: str):
        index = AssetIndexTable(
            id=id,
            name=name,
        )
        self.session.add(index)
        self.session.commit()
        self.session.refresh(index)
        self.session.close()
        return index

    def edit_index(
        self, index_id: str, name: Optional[str] = None, value: Optional[str] = None
    ):
        index = self.get_index(index_id)
        if name is not None:
            index.name = name
        if value is not None:
            index.value = value
        self.session.add(index)
        self.session.commit()
        self.session.refresh(index)
        self.session.close()
        return index

    def delete_index(self, index_id: str):
        index = self.get_index(index_id)
        self.session.delete(index)
        self.session.commit()
        self.session.close()
        return index
