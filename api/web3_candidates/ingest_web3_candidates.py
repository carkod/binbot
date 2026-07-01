import hashlib
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from sqlmodel import Session

from api.databases.crud.web3_candidates import Web3CandidatesCrud
from api.databases.web3_candidates import Web3CandidateCreate


KUCOIN_WEB_BASE = "https://www.kucoin.com"

KUCOIN_PAGES = {
    "kucoin_announcement": "https://www.kucoin.com/announcement",
    "kucoin_new_listings_page": "https://www.kucoin.com/announcement/new-listings",
    "kucoin_gemspace_ongoing": "https://www.kucoin.com/gemspace/ongoing",
    "kucoin_gemspace_newlisting": "https://www.kucoin.com/gemspace/newlisting",
    "kucoin_gempool": "https://www.kucoin.com/gempool",
    "kucoin_spotlight": "https://www.kucoin.com/spotlight-center",
    "kucoin_lockdrop": "https://www.kucoin.com/earn/x-lockdrop",
}

KEYWORDS = (
    "gempool",
    "gemspace",
    "spotlight",
    "burningdrop",
    "lockdrop",
    "x-lockdrop",
    "new listing",
    "gets listed",
    "get listed",
    "will list",
    "listing",
    "world premiere",
    "trading:",
    "trading starts",
    "trading will start",
    "token sale",
    "airdrop",
)

NOISE_LINK_TEXT = {
    "buy crypto",
    "markets",
    "trade",
    "derivatives",
    "earn",
    "more",
    "log in",
    "sign up",
    "about us",
    "blog",
    "news & announcements",
    "privacy policy",
    "terms of use",
    "api documentation",
    "download",
    "view more",
    "details",
    "apply now",
}

TOKEN_WITH_SYMBOL_RE = re.compile(
    r"(?P<name>[A-Z][A-Za-z0-9 ._\-'/&]{1,80}?)\s*\((?P<symbol>[A-Z0-9]{2,20})\)"
)
SYMBOL_ONLY_CONTEXT_RE = re.compile(
    r"\b(?:token|coin|amount|pool|rewards?)\s*\((?P<symbol>[A-Z0-9]{2,20})\)",
    re.IGNORECASE,
)
UTC_TIME_RE = re.compile(
    r"(?P<date>\d{1,2}/\d{1,2}|\d{4}-\d{2}-\d{2})"
    r"(?:\s+|,\s*)"
    r"(?P<time>\d{1,2}:\d{2})"
    r"\s*(?:\(UTC\)|UTC)?",
    re.IGNORECASE,
)


@dataclass
class LaunchCandidate:
    source: str
    source_type: str
    title: str
    url: str | None = None
    project_name: str | None = None
    symbol: str | None = None
    announced_at: datetime | None = None
    matched_keywords: list[str] = field(default_factory=list)
    extracted_times: list[str] = field(default_factory=list)
    confidence: float = 0.0
    raw: dict[str, Any] = field(default_factory=dict)

    def stable_id(self) -> str:
        # Source is intentionally excluded: the same announcement can appear
        # under multiple annType categories (e.g. latest-announcements AND
        # new-listings) and must hash to the same ID for deduplication.
        material = "|".join(
            [
                self.title,
                self.url or "",
                self.symbol or "",
                self.announced_at.isoformat() if self.announced_at else "",
            ]
        )
        return hashlib.sha256(material.encode("utf-8")).hexdigest()[:24]


class IngestWeb3Candidates:
    def __init__(
        self,
        session: Session | None = None,
        *,
        timeout: int = 15,
        sleep_s: float = 0.35,
    ) -> None:
        self.timeout = timeout
        self.sleep_s = sleep_s
        self.crud = Web3CandidatesCrud(session)
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (compatible; BinbotWeb3CandidateScanner/0.1)"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            }
        )

    def ingest_web3_candidates(self) -> dict[str, int]:
        candidates = self.run()
        created = 0
        updated = 0

        for candidate in candidates:
            _, was_created = self.crud.upsert(self.to_payload(candidate))
            if was_created:
                created += 1
            else:
                updated += 1

        logging.info(
            "Ingested web3 candidates: created=%s updated=%s total=%s",
            created,
            updated,
            len(candidates),
        )
        return {"created": created, "updated": updated, "total": len(candidates)}

    def run(self) -> list[LaunchCandidate]:
        return self.dedupe(self.fetch_all_page_candidates())

    def fetch_all_page_candidates(self) -> list[LaunchCandidate]:
        candidates: list[LaunchCandidate] = []

        for source, url in KUCOIN_PAGES.items():
            try:
                html = self.get_text(url)
            except Exception as exc:
                logging.warning(
                    "KuCoin page fetch failed for source=%s: %s", source, exc
                )
                continue

            candidates.extend(self.candidates_from_page(source, url, html))
            time.sleep(self.sleep_s)

        return candidates

    def candidates_from_page(
        self, source: str, page_url: str, html: str
    ) -> list[LaunchCandidate]:
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()

        candidates: list[LaunchCandidate] = []
        for anchor in soup.find_all("a"):
            text = self.clean_text(anchor.get_text(" ", strip=True))
            href = anchor.get("href")
            if not text or self.is_noise(text):
                continue

            candidate = self.candidate_from_text_block(
                source=source,
                page_url=urljoin(KUCOIN_WEB_BASE, str(href)) if href else page_url,
                text=text,
                raw={"kind": "anchor", "href": href, "text": text},
            )
            if candidate:
                candidates.append(candidate)

        visible_text = soup.get_text("\n", strip=True)
        lines = [self.clean_text(line) for line in visible_text.splitlines()]
        lines = [line for line in lines if line and not self.is_noise(line)]

        for index, line in enumerate(lines):
            context = " ".join(lines[max(0, index - 2) : min(len(lines), index + 3)])
            candidate = self.candidate_from_text_block(
                source=source,
                page_url=page_url,
                text=context,
                raw={"kind": "text_context", "line": line, "context": context},
            )
            if candidate:
                candidates.append(candidate)

        return self.dedupe(candidates)

    def candidate_from_text_block(
        self,
        source: str,
        page_url: str,
        text: str,
        raw: dict[str, Any],
    ) -> LaunchCandidate | None:
        if len(text) < 3:
            return None

        matched_keywords = self.match_keywords(text)
        symbol_data = self.extract_project_symbol(text)
        source_is_launch_page = any(
            key in source for key in ("gemspace", "gempool", "spotlight", "lockdrop")
        )

        if not matched_keywords and not (
            source_is_launch_page and symbol_data.get("symbol")
        ):
            return None

        title = text[:280].strip()
        confidence = 0.30
        if matched_keywords:
            confidence += 0.25
        if symbol_data.get("symbol"):
            confidence += 0.25
        if source_is_launch_page:
            confidence += 0.10

        return LaunchCandidate(
            source=source,
            source_type="page",
            title=title,
            url=page_url,
            project_name=symbol_data.get("project_name"),
            symbol=symbol_data.get("symbol"),
            matched_keywords=matched_keywords,
            extracted_times=self.extract_times(text),
            confidence=min(confidence, 1.0),
            raw=raw,
        )

    def get_text(self, url: str) -> str:
        return self.request_with_retries("GET", url).text

    def request_with_retries(
        self,
        method: str,
        url: str,
        params: dict[str, Any] | None = None,
        retries: int = 3,
    ) -> requests.Response:
        last_exc: Exception | None = None
        for attempt in range(retries):
            try:
                response = self.session.request(
                    method=method,
                    url=url,
                    params=params,
                    timeout=self.timeout,
                )
                if response.status_code == 429:
                    sleep_for = 2 + attempt * 2
                    logging.warning(
                        "Rate limited while fetching %s; sleeping %ss",
                        url,
                        sleep_for,
                    )
                    time.sleep(sleep_for)
                    last_exc = requests.HTTPError(response=response)
                    continue

                response.raise_for_status()
                return response
            except requests.RequestException as exc:
                last_exc = exc
                time.sleep(1 + attempt * 2)

        raise last_exc or requests.RequestException(
            f"All {retries} retries exhausted for {url}"
        )

    def to_payload(self, candidate: LaunchCandidate) -> Web3CandidateCreate:
        raw_payload = {
            "stable_id": candidate.stable_id(),
            "source_type": candidate.source_type,
            "matched_keywords": candidate.matched_keywords,
            "extracted_times": candidate.extracted_times,
            "confidence": candidate.confidence,
            "raw": candidate.raw,
        }
        return Web3CandidateCreate(
            source=candidate.source,
            project_name=candidate.project_name or candidate.title,
            symbol=candidate.symbol,
            announcement_url=candidate.url,
            announcement_title=candidate.title,
            announced_at=candidate.announced_at,
            raw_payload=raw_payload,
        )

    @staticmethod
    def clean_text(text: str) -> str:
        text = re.sub(r"\s+", " ", text or "")
        return text.strip(" \t\r\n|.-")

    @staticmethod
    def is_noise(text: str) -> bool:
        normalized = text.strip().lower()
        return (
            normalized in NOISE_LINK_TEXT
            or len(normalized) <= 2
            or normalized.startswith("image:")
            or normalized.startswith("copyright")
        )

    @staticmethod
    def match_keywords(text: str) -> list[str]:
        lower = text.lower()
        return [keyword for keyword in KEYWORDS if keyword in lower]

    @staticmethod
    def extract_project_symbol(text: str) -> dict[str, str | None]:
        match = TOKEN_WITH_SYMBOL_RE.search(text)
        if match:
            name = match.group("name").strip()
            symbol = match.group("symbol").strip()
            name = re.sub(
                r"^(Ended\s+)?KuCoin\s+Spotlight\s*-\s*",
                "",
                name,
                flags=re.IGNORECASE,
            )
            name = re.sub(
                r"^KuCoin\s+(Will\s+)?(List|Lists|Announces)\s+",
                "",
                name,
                flags=re.IGNORECASE,
            )
            return {"project_name": name.strip(), "symbol": symbol}

        symbol_context = SYMBOL_ONLY_CONTEXT_RE.search(text)
        if symbol_context:
            return {
                "project_name": None,
                "symbol": symbol_context.group("symbol").strip(),
            }

        return {"project_name": None, "symbol": None}

    @staticmethod
    def extract_times(text: str) -> list[str]:
        return [match.group(0) for match in UTC_TIME_RE.finditer(text)]

    @staticmethod
    def dedupe(candidates: list[LaunchCandidate]) -> list[LaunchCandidate]:
        # Sort first so the highest-quality candidate wins when two items share
        # the same stable_id (e.g. same announcement in multiple annType
        # categories — new-listings has higher confidence than latest-announcements).
        sorted_candidates = sorted(
            candidates,
            key=lambda c: (
                c.announced_at or datetime.min.replace(tzinfo=timezone.utc),
                c.confidence,
                c.source,
                c.title,
            ),
            reverse=True,
        )
        seen: set[str] = set()
        result: list[LaunchCandidate] = []
        for candidate in sorted_candidates:
            key = candidate.stable_id()
            if key in seen:
                continue
            seen.add(key)
            result.append(candidate)
        return result
