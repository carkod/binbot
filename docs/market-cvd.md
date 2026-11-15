# Stored KuCoin Futures CVD

The API reads Postgres only. The existing `streaming.main` worker hosts CVD
collection on its async event loop and runs blocking position sweeps sequentially
in a background thread. Public executions are collected even with no active bots
or open browsers. Both share one Python process, image, and container; no extra
service or interpreter is needed. The sweep cadence and breadth schedule are
unchanged. No pybinbot release is required.

## Rollout

1. Apply `uv run alembic upgrade head` from the repository root to create the
   history tables, then deploy the updated API.
2. Deploy/restart the existing **streaming** service. Its normal
   `uv run -m streaming.main` entry point starts collection automatically. Keep
   one streaming replica per database and allow 30 seconds for graceful shutdown
   (`stop_grace_period: 30s` in deployment Compose). No additional service,
   profile, image, or exchange credentials are needed for CVD. If the previous
   standalone `cvd_collector` was deployed, stop/remove it before restarting
   streaming so its ownership lock is released.
3. Observe checkpoint logs and `GET /charts/cvd-aggregate?interval=15m&limit=672`.
   Verify expected versus covered symbols, acknowledged subscriptions, fresh
   checkpoints, rejected payloads, and disconnect/flush errors. Allow three
   minutes after a full interval closes for late-arrival finalization.
4. After verifying real coverage, build terminal with
   `VITE_MARKET_CVD_ENABLED=true`. Its Dashboard then polls every 60 seconds.
   Leave it false while deploying schema and collector first.

Futures bot detail also reads this collector's per-symbol buckets. Deploy the
schema and API before the terminal; until a symbol has observations its CVD card
shows an empty state. The Dashboard flag controls only the market card.

The collector holds a Postgres **session advisory lock** on the same physical
connection that writes all batches. A second owner exits without writing. That
connection is destroyed on exit, releasing the lock; a lost/invalidated DB
connection stops collection rather than reconnecting without ownership.
SIGTERM stops the shards and saves a final partial checkpoint. Flush failures
are logged and restart only collection inside the streaming worker, with capped
exponential backoff and jitter (maximum 61 seconds). Position management continues
during CVD startup, database failures, ownership contention, and reconnects. A
position-worker exception still stops the service for its existing deployment
restart policy. The streaming healthcheck tracks position progress, including
quiet sweeps; CVD health is its stored API freshness/coverage and checkpoint logs.
Both stop on SIGTERM/SIGINT; the collector saves a final partial checkpoint while
the position thread finishes its current operation.

Sharing the process avoids a second interpreter and duplicate imports. The
WebSocket buffers, bounded deduplication window, minute buckets, and Postgres
history still consume resources; combining services does not remove that work.
No additional container memory reservation or image build is introduced. CPU
and memory limits now apply to positions and collection together. The standalone
`uv run -m streaming.cvd` entry point remains available for diagnostics; do not
run it alongside streaming against the same database.

## Protocol verification (2026-11-15)

References:

- [Classic Futures executions](https://www.kucoin.com/docs-new/3470084w0)
- [Classic connection, token, heartbeat and acknowledgements](https://www.kucoin.com/docs-new/websocket-api/base-info/introduction)
- [Classic rate limits](https://www.kucoin.com/docs-new/rate-limit-rule-classic)
- [KuCoin's original execution specification: side of liquidity taker](https://github.com/Kucoin/kucoin-futures-api-docs/blob/master/source/localizable/index.html.md)

Use a new public token from `POST /api/v1/bullet-public` on the Futures REST
host, wait for welcome, then subscribe to `/contractMarket/execution:{symbol}`
with `response: true`. Match the request ID to `ack`; timeout after 10 seconds.
The current docs allow unlimited futures topics per connection, at most 100
topics per request, 100 outgoing messages per 10 seconds per connection, and
800 concurrent connections per public IP. We deliberately shard into 100
symbols, send individual subscriptions at under five/second, and stagger
reconnects with capped exponential backoff and jitter (maximum 61 seconds).
All services on the same IP must share the exchange's connection budget.

Tokens and connections expire after 24 hours; rotate after 23 hours. Each shard
uses application JSON ping/pong, taking `pingInterval` and `pingTimeout` from
its token response in milliseconds. Ping every min(9 seconds, half interval),
and reconnect if its matching pong exceeds pingTimeout. Acks and executions
are read concurrently with throttled subscriptions and heartbeat.

A live public read-only capture found 717 active linear USDT contracts before
the registered-symbol intersection. Three individual subscriptions were acked.
A captured SOLUSDTM execution had side `sell`, price `71.738`, size `4`,
trade ID `1783308776639`, and exchange timestamp `1794772352120000000` ns.
SOL multiplier `0.1` converts it to **28.6952 USDT sell notional**. Receipt was
about 118 ms later. No private requests or orders were made.

## Universe, buckets and gaps

Every 15 minutes (and at startup), fetch the all-contracts REST list once and
intersect it with active registered KuCoin symbols. Include `status=Open`,
`settleCurrency=USDT`, `isInverse=false`, and a positive finite multiplier.
Quiet markets are included. No 24-hour turnover filter. Refresh failures retain
the last known universe, log an error, and retry after a minute.

Freeze membership and multipliers for each exchange UTC minute. A discovered
change reconnects subscriptions near a minute boundary, changes the universe
for the following minute, and marks interrupted coverage. Hash both symbol
membership and multipliers to identify changes, including equal-size population
swaps. Delisted symbols remain in their frozen minute, flagged partial if their
subscription was interrupted. New symbols become expected the following minute.

For each execution, add `price * contracts * multiplier` to buy or sell USDT
notional using the **taker** side. Timestamp is integer nanoseconds from the
exchange, never local arrival time. Reject malformed, nonfinite, nonpositive,
fractional contract size, before-start, over-120-seconds-late, and more-than-five-
seconds-future payloads. Accept late trades for up to 120 seconds and update
absolute bucket totals, even after the UTC minute closes. Finalize only after
that lateness period. A hard two-million-ID memory cap rejects further new
executions until old minutes expire and marks affected coverage incomplete.

An acknowledged subscription covering the entire minute counts as covered even
with zero executions. Startup, subscription failure, reconnect, rejected data,
event-loop stalls and metadata changes mark affected minutes partial. After
disconnect, invalidate coverage back 30 seconds to conservatively account for
heartbeat detection delay. A scheduler stall marks every minute from the last
tick through resumption partial while retaining healthy subscription acks;
coverage can resume with the next full minute. Acks do not heal earlier gaps.
Current intervals are always partial. An entirely absent minute is an outage,
never a zero.

Persist per-symbol buckets and market minute rollups atomically every ten
seconds in batches of 500, using absolute upserts. Read charts from rollups so
queries scan at most 10,080 minute rows instead of ~7.9 million symbol rows.
Keep seven days, indexed by minute for retention deletes. Expect approximately
1.12 million symbol rows/day for a 780-symbol universe; provision Postgres disk,
autovacuum and I/O accordingly. No execution-level database rows are stored.

## Retry and crash semantics

Dedup keys include source, symbol and trade ID, retained for the mutable minute
window (maximum 120 seconds late plus the current minute). Retried checkpoint
batches replace absolute totals rather than adding them, so an ambiguous commit
cannot double-count the same batch. The single owner prevents worker overlap.

On restart, restore recent saved absolute buckets and their frozen universe.
Reject executions timestamped before this process's startup or at or below the
maximum saved exchange timestamp for that symbol. This durable replay cutoff
also fences saved executions up to five seconds ahead of the local clock during
a rapid restart. The per-symbol cutoff stays fixed for the process lifetime,
so new within-run out-of-order executions above it remain eligible under the
120-second lateness limit. Distinct executions at or below the cutoff are
deliberately dropped when their replay status is uncertain. Restored minutes
permanently lose complete coverage. This deliberately sacrifices delayed
executions across a restart rather than claiming exactly-once history.
Executions received after the last successful checkpoint can be lost.
WebSocket reconnect has **no
backfill guarantee**, and history begins at collector startup. Missing minutes
remain gaps in the API, including during full collector outages.

## API and chart meaning

`GET /charts/cvd-aggregate?interval=15m&limit=672` accepts only `15m` and limits
1–672. Return oldest-first fixed UTC windows ending with the current interval,
including explicit empty windows when collection exists. Empty history returns
an empty list. `reset_at` is the fixed selected window start and CVD starts at
zero there, adding each observed bucket delta. It is an **observed** cumulative
sum, including partial intervals; no missing trades are imputed.

Each interval returns buy/sell notionals, observed CVD, expected-symbol maximum,
covered-symbol minimum, observed minute count, complete/gap/current flags and
universe-change flag. A complete interval requires all 15 finalized minutes,
full symbol coverage and one unchanged nonempty universe. Empty windows return
null buy/sell/CVD and unknown expected count; full outages do not silently reuse
a historic population. The response includes source, latest checkpoint,
staleness (>90 seconds) and partial-history status. The chart breaks lines at
partial/absent intervals and population changes, preserves numerical hover
values, and marks incomplete points with open diamonds.

### Individual futures symbols

`GET /charts/cvd-symbol?symbol=SOLUSDTM&interval=1m&limit=15` reads the same
collector's `cvd_bucket` rows, filtered by source and symbol. Symbols are
case-insensitive alphanumeric KuCoin contract IDs (up to 64 characters). Only
`1m` is supported; `limit` is bounded to 1–10080 minutes (seven days), default 15.
No additional exchange requests, collector or migration are needed.

The futures bot's order-book analysis tab shows a rolling 15-minute window and
polls every 30 seconds. Browser WebSocket collection and IndexedDB CVD history are superseded;
spread/depth polling and its in-memory history remain independent. Switching bots
shows only the requested symbol's cached response or its loading state.

The response adds `symbol` to the market CVD response shape. Each point is one
minute; expected/covered counts are 1 for a recorded/covered symbol, respectively.
Quiet covered minutes have zero buy/sell; missing minutes have null notionals/CVD,
unknown expected count, and zero coverage. Completeness requires that symbol's
coverage and the minute's finalized checkpoint. Unrelated markets' outages and
universe changes do not affect it. `universe_changed` here means a change to this
contract's multiplier between observed minutes. Lines break at coverage gaps and
multiplier changes, and hover values retain the API precision.

Freshness uses the latest checkpoint containing this symbol, so an active market
cannot mask a stale or delisted one. Collected history remains readable after
delisting until seven-day retention expires. CVD starts at zero at `reset_at`,
accumulates only observed minute deltas, and rebases as the window advances. The
current minute and closed minutes awaiting the two-minute late-arrival allowance
remain partial. No executions lost during outages or before deployment are
backfilled; existing browser-only observations are not merged into central data.

Run `make format`, `make test`, `make test-streaming`, `make test-cronjobs`, and
terminal test/lint/type-check/build scripts. PostgreSQL-specific ownership and
upsert tests require `CVD_TEST_POSTGRES_URL` pointing to an **isolated disposable
database**, never the live operational DB. The throughput test feeds 50,000
executions across 780 symbols without per-execution database I/O.

Local validation also exercised the full 717-contract public universe against an
isolated disposable Postgres instance: eight connections acknowledged all 717
subscriptions, checkpointed real execution notionals every ten seconds, and
reported 717/717 continuous coverage after startup. This is a local protocol and
load check, not a production deployment or historical backfill.
