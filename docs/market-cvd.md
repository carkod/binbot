# Stored KuCoin Futures CVD

The existing `streaming.main` worker collects public executions independently of
bots and browsers, alongside position management in the same process/container.
No extra service, image, credentials or pybinbot release is required. Collection
uses the registered, active linear USDT futures universe, refreshed every 15
minutes. Minute delta is taker buy minus sell USDT notional
(`price × contracts × multiplier`).

## Rollout and monitoring

1. Run `uv run alembic upgrade head`, then deploy the updated API.
2. Restart the existing streaming service. Keep one replica per database and
   allow 30 seconds for graceful shutdown (`stop_grace_period: 30s`).
3. Check checkpoint logs and `GET /charts/cvd-aggregate?limit=672`: expected versus
   covered symbols, acknowledged subscriptions, freshness, rejected payloads and
   disconnect/flush errors. Allow two minutes after a minute closes to finalize.

Deploy terminal after the schema and API. The Dashboard card shows seven days
with 15-minute points and 60-second polling. Futures bot detail uses the same
stored symbol buckets (15 minutes, one-minute points, 30-second polling). Both
handle empty history while collection starts.

Endpoint parameters, reset semantics, coverage and gap fields are documented in
FastAPI Swagger at `/docs` under **charts** (`/charts/cvd-aggregate` and
`/charts/cvd-symbol`). Chart requests read Postgres only.

## Storage and recovery

- Save absolute per-symbol minute buckets and market rollups atomically every ten
  seconds. Retain seven days: about 1.12 million symbol rows/day for 780 symbols.
  Provision Postgres disk, autovacuum and I/O accordingly.
- In memory, retain exact execution IDs grouped by exchange minute and symbol;
  release them only after a successful checkpoint and expiry of the two-minute
  late-arrival window. The two-million-ID safety cap remains in force.
  Checkpoint logs include `dedup_entries`, the current retained ID count, alongside
  cumulative `trades`. A local 100,000-execution replay across 780 symbols retained
  10.9 MiB of traced allocations, down from 19.7 MiB with per-trade tuple keys;
  these measurements exclude imported dependencies and other worker memory.
- Each execution WebSocket shard uses a 16-frame receive queue high-water mark
  to apply backpressure, with a 64 KiB message limit. This replaces the previous
  4,096-frame queue. Larger messages close the connection and invalidate coverage
  through the normal disconnect path. Monitor disconnects, rejected executions,
  checkpoint freshness and container memory after rollout. See the
  [WebSocket buffer documentation](https://websockets.readthedocs.io/en/stable/topics/memory.html).
- A session advisory lock on the writer connection prevents overlapping owners.
  Retried checkpoints replace totals without adding them again. Lost ownership
  or database failures restart collection with backoff; position management
  continues. The service healthcheck tracks positions; use CVD logs and API
  freshness/coverage to monitor collection.
- History starts at collection startup. Reconnects do not backfill; unflushed
  executions may be lost. Restart restores saved totals, marks restored minutes
  partial, and drops executions before startup or at/below the saved per-symbol
  timestamp cutoff. Coverage resumes with full acknowledged minutes; quiet
  covered markets count as zero, while outages remain gaps.

Collector code lives in [streaming/cvd](../streaming/cvd); unsigned REST and
WebSocket transport lives in [streaming/shared](../streaming/shared). See
[KuCoin executions](https://www.kucoin.com/docs-new/3470084w0),
[connection and heartbeat](https://www.kucoin.com/docs-new/websocket-api/base-info/introduction)
and [rate limits](https://www.kucoin.com/docs-new/rate-limit-rule-classic).

Run the root formatting, tests and entry-point smoke checks. PostgreSQL ownership
and checkpoint tests additionally require `CVD_TEST_POSTGRES_URL` pointing to an
isolated disposable database.
