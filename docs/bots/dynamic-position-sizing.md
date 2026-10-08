---
layout: default
title: Dynamic position sizing
---

# Dynamic position sizing

`dynamic_position_sizing` defaults to `false` on live and paper bots. Enabling it
selects `DynamicPositionSizing` in the KuCoin futures lifecycle. Both long and
short positions are supported. Spot and margin bots reject this setting.

The bot needs `0 < stop_loss < 100`, `take_profit > 0`, `trailing_profit > 0`, and
`0 < trailing_deviation < 100`. The trailing parameters configure the fallback.
The persisted deal field `position_size_pct` defaults to **25** and accepts
percentages greater than zero through 100.

- An adverse move of `stop_loss` percent reduces the current contracts by
  `position_size_pct` percent, using a reduce-only market order.
- A favorable move of `take_profit` percent adds the same percentage of the
  current contracts. It checks the futures wallet and
  `required_margin_for_contracts` first, using the symbol's configured leverage.
- Thresholds initially use the entry price, then reset around each adjustment's
  confirmed average fill price. There is at most one adjustment per tick;
  a price gap does not submit a batch of catch-up orders.
- Contract adjustments round down to the exchange lot size. When a reduction
  rounds to zero, the remaining minimum position closes. An increase below one
  lot falls back to trailing profit.

For example, with 100 contracts, entry 100, `stop_loss=5`, `take_profit=10`, and
`position_size_pct=25`, a long reduces 25 contracts at price 95. After a fill at
95, its next thresholds are 90.25 and 104.5; the next adjustment uses the
remaining 75 contracts. A short uses the opposite price directions.

When an increase is unaffordable, the bot logs the reason, switches
`dynamic_position_sizing` off, enables `trailing`, clears fixed take profit, and
continues through the normal lifecycle in the same tick. The switch persists
until explicitly re-enabled. Paper adjustments simulate fills without a wallet
limit; they do not place exchange orders or read live account positions.

While enabled, sizing owns the SL/TP flow and bypasses strategy parameter
updates, reversal, full-position stops, and trailing profit. Existing exchange
stops are cancelled when sizing starts. Consequently, reductions depend on the
streaming service running. Normal strategy management resumes after fallback.

`position_size_reference_price` persists the threshold anchor.
`position_size_order` persists an adjustment's client ID and pre-order state
before submission. New intents start in `prepared`; `submitting` is committed
before calling the exchange. A restart discards a `prepared` intent and restores
normal trailing/stop protection, because no submission could have occurred.
Legacy intents default to `submitting`, preserving their uncertain outcome.

For uncertain submissions, lookup remains authoritative. After at least three
explicit missing-order responses spanning 60 seconds, the worker retries using
the **same client ID**. The counter and first-missing time survive restarts.
Duplicate-ID rejections keep the intent pending for reconciliation; they never
count as fills. A successful lookup resets the missing counter. Invalid
parameters, rate limits, and server failures do not count as missing orders.
Increases recheck margin at the latest price before retrying. If funds are no
longer sufficient, normal protection resumes while the uncertain ID is retained
for reconciliation, with further submissions disabled. Terminal partial fills
use only their actual filled quantity. This follows KuCoin's
[client order ID contract](https://www.kucoin.com/docs-new/rest/futures-trading/orders/add-order).

`opening_qty` preserves the original fill; `current_position_qty` and
`base_order_size` track the remaining contracts. Adds update the weighted entry
price. Each confirmed adjustment remains in order history, including paper
orders. Existing simple price-return reports do not aggregate realized PnL
across these partial exits.

## Installation

This change spans `binbot` and the shared `pybinbot` package. Install or release
the updated shared models before starting API/streaming workers, and apply
Alembic revision `a7b4e9c261f0`. The migration adds missing fields, backfills null
defaults even when columns already exist, and can be replayed. No existing bot
is opted in by the migration.

For local validation against the sibling checkout:

```sh
uv pip install --no-deps --reinstall ../pybinbot
UV_NO_SYNC=1 make format
UV_NO_SYNC=1 make test
UV_NO_SYNC=1 make test-streaming test-cronjobs
```

`UV_NO_SYNC` keeps the local shared-package build in place during these checks.
Production dependency locking must use the released shared package containing
these fields.
