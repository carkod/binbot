from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Any

from sqlmodel import Session, col, select

from databases.utils import get_db_session
from databases.web3_candidates import (
    Web3CandidateCreate,
    Web3CandidateTable,
    Web3CandidateUpdate,
)


class Web3CandidatesCrud:
    def __init__(self, session: Session | None = None):
        self._external_session = session

    def create(self, payload: Web3CandidateCreate) -> Web3CandidateTable:
        row = Web3CandidateTable(**payload.model_dump())
        with get_db_session(self._external_session) as session:
            session.add(row)
            session.commit()
            session.refresh(row)
            if self._external_session is None:
                session.expunge(row)
        return row

    def get(self, candidate_id: int) -> Web3CandidateTable | None:
        with get_db_session(self._external_session) as session:
            row = session.get(Web3CandidateTable, candidate_id)
            if row is not None and self._external_session is None:
                session.expunge(row)
            return row

    def get_existing(
        self,
        *,
        source: str,
        announcement_url: str | None,
        announcement_title: str | None,
        symbol: str | None,
    ) -> Web3CandidateTable | None:
        if announcement_url is not None:
            # URL uniquely identifies an announcement regardless of which
            # annType category it was fetched from, so don't filter on source.
            # This prevents cross-listed items (same URL, different category)
            # from being inserted as duplicates on re-ingestion.
            stmt = select(Web3CandidateTable).where(
                Web3CandidateTable.announcement_url == announcement_url
            )
        else:
            stmt = (
                select(Web3CandidateTable)
                .where(Web3CandidateTable.source == source)
                .where(Web3CandidateTable.announcement_title == announcement_title)
                .where(Web3CandidateTable.symbol == symbol)
            )

        with get_db_session(self._external_session) as session:
            row = session.exec(stmt).first()
            if row is not None and self._external_session is None:
                session.expunge(row)
            return row

    def upsert(self, payload: Web3CandidateCreate) -> tuple[Web3CandidateTable, bool]:
        existing = self.get_existing(
            source=payload.source,
            announcement_url=payload.announcement_url,
            announcement_title=payload.announcement_title,
            symbol=payload.symbol,
        )
        if existing is None or existing.id is None:
            return self.create(payload), True

        updated = self.update(existing.id, payload.model_dump(exclude_unset=True))
        if updated is None:
            return self.create(payload), True
        return updated, False

    def list(
        self,
        *,
        source: str | None = None,
        status: str | None = None,
        symbol: str | None = None,
        chain: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[Web3CandidateTable]:
        stmt = select(Web3CandidateTable)
        if source is not None:
            stmt = stmt.where(Web3CandidateTable.source == source)
        if status is not None:
            stmt = stmt.where(Web3CandidateTable.status == status)
        if symbol is not None:
            stmt = stmt.where(Web3CandidateTable.symbol == symbol)
        if chain is not None:
            stmt = stmt.where(Web3CandidateTable.chain == chain)
        stmt = (
            stmt.order_by(col(Web3CandidateTable.created_at).desc())
            .offset(offset)
            .limit(limit)
        )
        with get_db_session(self._external_session) as session:
            rows = session.exec(stmt).all()
            if self._external_session is None:
                for row in rows:
                    session.expunge(row)
            return rows

    def update(
        self,
        candidate_id: int,
        payload: Web3CandidateUpdate | dict[str, Any],
    ) -> Web3CandidateTable | None:
        with get_db_session(self._external_session) as session:
            row = session.get(Web3CandidateTable, candidate_id)
            if row is None:
                return None

            updates = (
                payload.model_dump(exclude_unset=True)
                if isinstance(payload, Web3CandidateUpdate)
                else payload
            )
            for field, value in updates.items():
                setattr(row, field, value)
            row.updated_at = datetime.now(timezone.utc)
            session.add(row)
            session.commit()
            session.refresh(row)
            if self._external_session is None:
                session.expunge(row)
            return row

    def delete(self, candidate_id: int) -> Web3CandidateTable | None:
        with get_db_session(self._external_session) as session:
            row = session.get(Web3CandidateTable, candidate_id)
            if row is None:
                return None

            deleted = row.model_copy()
            session.delete(row)
            session.commit()
            return deleted
