---
layout: default
title: Dynamic position sizing
---

# Dynamic position sizing

`dynamic_position_sizing` defaults to `false`. When enabled on a KuCoin
futures bot with `trailing=true`, it adds contracts only when the lifecycle
reaches `deal.trailing_profit_price`. Both long and short positions are
supported. Spot and margin bots reject this setting.

The existing shared model requires `0 < stop_loss < 100`, `take_profit > 0`,
`trailing_profit > 0`, and `0 < trailing_deviation < 100`. Sizing uses the
trailing-profit trigger, not `take_profit`; fixed take-profit exits are
suppressed while trailing-based sizing is enabled. The persisted deal field
`position_size_pct` defaults to **25** and accepts percentages through 100.

- A trailing-profit trigger arms or tightens the full-position trailing stop
  and requests an increase of `position_size_pct` percent of current contracts.
- The next trigger is persisted in `deal.trailing_profit_price`, using the
  current price and `trailing_profit`. Repeated ticks or restarts at the same
  price do not repeat an increase. An active pending order prevents a second
  increase.
- Each increase checks the futures wallet and `required_margin_for_contracts`,
  using the bot's saved leverage. Quantities round down to exchange lots.
- Cumulative partial fills update the weighted entry and current quantity while
  the order remains active. Each observation resizes native protection using
  the confirmed quantity, even if the position endpoint still reports the old
  size. The pending intent remains until terminal; the pre-order snapshot makes
  repeated polls and restarts idempotent. A delayed fill price does not delay
  protecting observed contracts. Terminal history records the cumulative fill
  once. Fills do not
  reset the trailing trigger, stop loss, or trailing stop around the fill price.
  Exchange protection is reconciled to cover the new full position quantity,
  even during the normal stop-replacement cooldown, without loosening its price.
- Reaching `deal.trailing_stop_loss_price` closes the **entire live position**,
  including at exact equality. The trailing exit takes precedence over pending
  sizing lookups and further increases. Pending increases are disabled and open
  orders are cancelled before a full close reads the exchange position quantity.
- Stop loss continues to close the whole position; sizing never submits partial
  stop-loss reductions. Native full-position stops remain enabled.

For example, a short entered at 0.06320 with `trailing_profit=4.5`,
`trailing_deviation=3`, and 24 contracts reaches its first trailing trigger at
approximately 0.06035. At 0.06028 it arms a trailing stop near 0.06208 and adds
6 contracts. At 0.05745 it tightens the stop to approximately 0.05917 and adds
7 more. A rebound to 0.05917 closes all 37 contracts; it does not buy back only
25 percent and resume sizing.

When an increase is unaffordable or below one exchange lot, sizing disables
itself, leaves trailing enabled, and clears fixed take profit. The armed
trailing stop is preserved. Normal strategy evaluation and protective exits
run whether or not sizing is enabled.

`position_size_order` persists an increase's client ID and pre-order state
before submission. New intents start in `prepared`; `submitting` is committed
before the API call. A restart discards a `prepared` intent and restores normal
protection because no submission could have occurred. Legacy intents default
to `submitting`; old partial reduction intents can still be reconciled, but are
never resubmitted. `position_size_reference_price` remains for compatibility
and no longer defines independent sizing thresholds.

Uncertain submissions are looked up by their original client ID. After at least
three explicit missing-order responses over 60 seconds, recovery retries the
same ID while the bot remains active and sizing is enabled. The handler also
recognizes KuCoin's `error.getOrder.orderNotExist` response. Duplicate-ID
rejections retain the pending intent; they do not count as fills. Retry counters
survive restarts, and increases recheck margin before retrying. Invalid
parameters, rate limits, and server failures do not count as missing orders;
lookup failures do not suppress protective lifecycle exits.

`opening_qty` remains historical; `current_position_qty` and `base_order_size`
track live contracts. Confirmed increases remain in order history. No shared
model changes or new database migration are needed for this behavior update.

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
