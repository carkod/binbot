"""Tests for cross-category deduplication and retry/rate-limit handling."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
import requests
from sqlmodel import Session, delete

from api.databases.crud.web3_candidates import Web3CandidatesCrud
from api.databases.web3_candidates import Web3CandidateCreate, Web3CandidateTable
from tests import conftest
from api.web3_candidates.ingest_web3_candidates import (
    LaunchCandidate,
    IngestWeb3Candidates,
)


def _make_session() -> Session:
    assert conftest._test_engine is not None
    return Session(conftest._test_engine, expire_on_commit=False)


@pytest.fixture(autouse=True)
def _clean_candidates():
    with _make_session() as session:
        session.execute(delete(Web3CandidateTable))
        session.commit()
    yield
    with _make_session() as session:
        session.execute(delete(Web3CandidateTable))
        session.commit()


def _make_candidate(source: str, confidence: float = 0.70) -> LaunchCandidate:
    return LaunchCandidate(
        source=source,
        source_type="api",
        title="KuCoin Will List FOOBAR (FBR)",
        url="https://www.kucoin.com/announcement/kucoin-will-list-fbr",
        project_name="FOOBAR",
        symbol="FBR",
        announced_at=datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc),
        matched_keywords=["listing"],
        confidence=confidence,
    )


# ---------------------------------------------------------------------------
# stable_id
# ---------------------------------------------------------------------------


def test_stable_id_same_for_different_sources():
    """Same announcement in two annType categories must produce the same stable_id."""
    latest = _make_candidate("kucoin_announcements:latest-announcements")
    new_listing = _make_candidate("kucoin_announcements:new-listings")
    assert latest.stable_id() == new_listing.stable_id()


def test_stable_id_differs_for_different_urls():
    a = _make_candidate("kucoin_announcements:new-listings")
    b = LaunchCandidate(
        source="kucoin_announcements:new-listings",
        source_type="api",
        title="KuCoin Will List BARFOO (BFR)",
        url="https://www.kucoin.com/announcement/kucoin-will-list-bfr",
        symbol="BFR",
        announced_at=datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc),
        confidence=0.70,
    )
    assert a.stable_id() != b.stable_id()


# ---------------------------------------------------------------------------
# dedupe
# ---------------------------------------------------------------------------


def test_dedupe_collapses_cross_category_duplicates():
    """run()'s dedupe must keep only one candidate when the same announcement
    appears under multiple annType categories."""
    latest = _make_candidate(
        "kucoin_announcements:latest-announcements", confidence=0.70
    )
    new_listing = _make_candidate("kucoin_announcements:new-listings", confidence=0.80)
    result = IngestWeb3Candidates.dedupe([latest, new_listing])
    assert len(result) == 1
    # new-listings has higher confidence and sorts first (descending), so it wins
    assert result[0].source == "kucoin_announcements:new-listings"


# ---------------------------------------------------------------------------
# get_existing — URL-first lookup
# ---------------------------------------------------------------------------


def test_get_existing_finds_row_across_sources():
    """get_existing() must find an existing row by URL regardless of which
    annType source the row was originally stored under."""
    with _make_session() as session:
        crud = Web3CandidatesCrud(session)
        crud.create(
            Web3CandidateCreate(
                source="kucoin_announcements:latest-announcements",
                project_name="FOOBAR",
                symbol="FBR",
                announcement_url="https://www.kucoin.com/announcement/kucoin-will-list-fbr",
                announcement_title="KuCoin Will List FOOBAR (FBR)",
                announced_at=datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc),
            )
        )

        found = crud.get_existing(
            source="kucoin_announcements:new-listings",
            announcement_url="https://www.kucoin.com/announcement/kucoin-will-list-fbr",
            announcement_title="KuCoin Will List FOOBAR (FBR)",
            symbol="FBR",
        )

    assert found is not None
    assert found.symbol == "FBR"


def test_get_existing_returns_none_for_unknown_url():
    with _make_session() as session:
        crud = Web3CandidatesCrud(session)
        found = crud.get_existing(
            source="kucoin_announcements:new-listings",
            announcement_url="https://www.kucoin.com/announcement/no-such-item",
            announcement_title="No Such Item",
            symbol="NSI",
        )
    assert found is None


def test_get_existing_no_url_still_uses_source_title_symbol():
    """Without a URL the lookup must still scope to source+title+symbol."""
    with _make_session() as session:
        crud = Web3CandidatesCrud(session)
        crud.create(
            Web3CandidateCreate(
                source="kucoin_announcement",
                project_name="FOOBAR",
                symbol="FBR",
                announcement_url=None,
                announcement_title="KuCoin Will List FOOBAR (FBR)",
            )
        )

        # same title+symbol but different source → should not find it
        not_found = crud.get_existing(
            source="kucoin_announcements:new-listings",
            announcement_url=None,
            announcement_title="KuCoin Will List FOOBAR (FBR)",
            symbol="FBR",
        )
        # same source → should find it
        found = crud.get_existing(
            source="kucoin_announcement",
            announcement_url=None,
            announcement_title="KuCoin Will List FOOBAR (FBR)",
            symbol="FBR",
        )

    assert not_found is None
    assert found is not None


# ---------------------------------------------------------------------------
# upsert end-to-end: cross-listed item must not produce a duplicate row
# ---------------------------------------------------------------------------


def test_upsert_cross_listed_announcement_no_duplicate():
    """Upserting the same announcement URL under two different annType sources
    must result in exactly one row, not two."""
    with _make_session() as session:
        crud = Web3CandidatesCrud(session)

        payload_latest = Web3CandidateCreate(
            source="kucoin_announcements:latest-announcements",
            project_name="FOOBAR",
            symbol="FBR",
            announcement_url="https://www.kucoin.com/announcement/kucoin-will-list-fbr",
            announcement_title="KuCoin Will List FOOBAR (FBR)",
            announced_at=datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc),
        )
        payload_new_listing = Web3CandidateCreate(
            source="kucoin_announcements:new-listings",
            project_name="FOOBAR",
            symbol="FBR",
            announcement_url="https://www.kucoin.com/announcement/kucoin-will-list-fbr",
            announcement_title="KuCoin Will List FOOBAR (FBR)",
            announced_at=datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc),
        )

        _, created_first = crud.upsert(payload_latest)
        _, created_second = crud.upsert(payload_new_listing)

        rows = crud.list(symbol="FBR")

    assert created_first is True
    assert created_second is False
    assert len(rows) == 1


# ---------------------------------------------------------------------------
# request_with_retries — persistent 429 raises HTTPError, not AssertionError
# ---------------------------------------------------------------------------


def _make_ingester() -> IngestWeb3Candidates:
    ingester = IngestWeb3Candidates.__new__(IngestWeb3Candidates)
    ingester.timeout = 5
    ingester.session = requests.Session()
    return ingester


def _make_429_response() -> requests.Response:
    resp = requests.Response()
    resp.status_code = 429
    return resp


def test_request_with_retries_all_429_raises_http_error():
    """When every attempt returns 429, raise HTTPError rather than AssertionError."""
    ingester = _make_ingester()
    with (
        patch("web3_candidates.ingest_web3_candidates.time.sleep"),
        patch.object(ingester.session, "request", return_value=_make_429_response()),
    ):
        with pytest.raises(requests.HTTPError):
            ingester.request_with_retries("GET", "https://example.com", retries=2)


def test_request_with_retries_eventual_success_after_429():
    """A 429 followed by a successful response must return the good response."""
    ingester = _make_ingester()
    good = requests.Response()
    good.status_code = 200
    good._content = b""

    responses = [_make_429_response(), good]
    with (
        patch("web3_candidates.ingest_web3_candidates.time.sleep"),
        patch.object(ingester.session, "request", side_effect=responses),
    ):
        result = ingester.request_with_retries("GET", "https://example.com", retries=3)

    assert result.status_code == 200


# ---------------------------------------------------------------------------
# fetch_all_page_candidates — persistent 429 logs and skips, does not abort
# ---------------------------------------------------------------------------


def test_fetch_all_page_candidates_skips_rate_limited_page():
    """A page that keeps returning 429 must be logged and skipped; other
    pages in KUCOIN_PAGES must still be attempted."""
    ingester = IngestWeb3Candidates.__new__(IngestWeb3Candidates)
    ingester.timeout = 5
    ingester.sleep_s = 0
    ingester.session = requests.Session()

    mock_request = MagicMock(return_value=_make_429_response())

    with (
        patch("web3_candidates.ingest_web3_candidates.time.sleep"),
        patch.object(ingester.session, "request", side_effect=mock_request),
    ):
        # Should complete without raising; all pages rate-limited → no candidates
        result = ingester.fetch_all_page_candidates()

    assert result == []
    # Each page triggered at least one HTTP call (retries=3 default)
    assert mock_request.call_count > 0
