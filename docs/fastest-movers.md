# Fastest futures movers

`GET /charts/fastest_movers?limit=10` ranks KuCoin futures contracts by their
actual price change over approximately one hour. The response contains separate
`gainers` and `losers` lists, newest snapshot time, comparison time, and each
contract's one-hour move, optional three-hour move, rolling 24-hour change,
last price, and 24-hour turnover.

When market breadth is configured for KuCoin, its existing ingest saves prices
for all active futures contracts every 15 minutes. The hourly top-gainers ingest saves the
same prices from its own response. Neither path makes another exchange request
for this feature. Only five hours of these per-contract prices are retained.

The endpoint compares the latest stored price with the snapshot closest to one
hour earlier, accepting a 50–70 minute gap. It also uses a snapshot about three
hours earlier when available. Contracts missing the one-hour price comparison
are omitted; contracts missing only the three-hour comparison return `null` for
that field. Until two compatible snapshots exist, both lists are empty and
`comparison_at` is `null`.

This is a ranking of observed moves, not a forecast or a liquidity filter.
The dashboard shows the snapshot time so an interrupted ingest is visible.
