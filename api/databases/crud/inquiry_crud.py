from typing import Sequence
from sqlmodel import Session, select
from inquiries.models import InquiryBase
from databases.tables.inquiry_table import InquiryTable
from databases.utils import get_session
from uuid import UUID


class InquiryCrud:
    def __init__(self, session: Session | None = None):
        self._external_session = session

    def _get_session(self) -> Session:
        if self._external_session is not None:
            return self._external_session
        return get_session()

    def create_inquiry(self, inquiry: InquiryBase) -> InquiryTable:
        session = self._get_session()
        inquiry_table = InquiryTable(**inquiry.model_dump())
        session.add(inquiry_table)
        session.commit()
        session.refresh(inquiry_table)
        return inquiry_table

    def get_inquiry(self, inquiry_id: str | UUID) -> InquiryTable | None:
        if isinstance(inquiry_id, str):
            inquiry_id = UUID(inquiry_id)
        session = self._get_session()
        return session.get(InquiryTable, inquiry_id)

    def get_inquiries(
        self, offset: int = 0, limit: int = 100, reason: str | None = None
    ) -> Sequence[InquiryTable]:
        session = self._get_session()
        statement = select(InquiryTable)
        if reason:
            statement = statement.where(InquiryTable.reason == reason)
        statement = statement.offset(offset).limit(limit)
        result = session.exec(statement).all()
        return result

    def delete_inquiry(self, inquiry_id: UUID) -> UUID | None:
        session = self._get_session()
        inquiry = session.get(InquiryTable, inquiry_id)
        if inquiry:
            session.delete(inquiry)
            session.commit()
            return inquiry.id
        return None
