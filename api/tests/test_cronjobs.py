from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock

from apscheduler.schedulers.blocking import BlockingScheduler

import cronjobs.main as cronjobs


def test_futures_snapshot_ingestion_uses_fixed_utc_half_hours(monkeypatch):
    scheduler = BlockingScheduler()
    monkeypatch.setattr(scheduler, "start", Mock())
    monkeypatch.setattr(cronjobs, "BlockingScheduler", lambda: scheduler)
    monkeypatch.setattr(
        cronjobs, "Config", lambda: SimpleNamespace(timezone="Pacific/Auckland")
    )
    monkeypatch.setattr(cronjobs, "configure_logging", Mock())
    monkeypatch.setattr(cronjobs, "independent_session", Mock())
    for name in (
        "ConsolidatedAccounts",
        "MarketDominationController",
        "SymbolDataEtl",
        "SignalsCrud",
        "TopGainersLosersSeriesCrud",
        "IngestWeb3Candidates",
    ):
        monkeypatch.setattr(cronjobs, name, Mock())

    cronjobs.main()

    job = scheduler.get_job("ingest_top_gainers_losers")
    assert job is not None
    first = job.trigger.get_next_fire_time(
        None, datetime(2026, 11, 27, 12, 7, tzinfo=timezone.utc)
    )
    assert first == datetime(2026, 11, 27, 12, 30, tzinfo=timezone.utc)
    assert job.trigger.get_next_fire_time(first, first) == datetime(
        2026, 11, 27, 13, 0, tzinfo=timezone.utc
    )
    assert job.coalesce is True
    assert job.misfire_grace_time == 60
