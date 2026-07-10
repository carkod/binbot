# Grid Ladders

```
┌───────────────────────────────────────────────────────────────┐
│  CREATE                                                        │
│  POST /grid-ladders: range_low/high, level_count, total_margin │
│  → calculate_grid_levels() computes N price levels             │
│  → ladder status = pending                                     │
└──────────────────────────────┬────────────────────────────────┘
                                │
                                ▼
┌───────────────────────────────────────────────────────────────┐
│  INITIAL PLACEMENT  (_place_initial_entries)                   │
│  Both sides placed resting on the exchange at once:            │
│    buy entry  @ low-side price levels                          │
│    sell entry @ high-side price levels                         │
│  → ladder status = active                                      │
└──────────────────────────────┬────────────────────────────────┘
                                │
                                ▼
┌───────────────────────────────────────────────────────────────┐
│  ACTIVE — oscillation loop (repeats until closed)               │
│                                                                  │
│    FLAT ──fill──► GUARD (cancel opposite, live_side = X)        │
│     ▲                        │                                  │
│     │                        ▼                                  │
│     └──── RE-ARM both sides ◄── TP fill ◄── LIVE (X)            │
│                                                                  │
│   (see the oscillation timeline further below for the          │
│    play-by-play of one cycle through this loop)                 │
└───────┬──────────────────────────────────────────────┬────────┘
        │ range-break / stale timeout / manual close    │ conflicting
        ▼                                                │ fill race
┌───────────────────────┐                    ┌───────────▼────────────┐
│  CLOSED                │                    │  ERROR (manual review) │
│  position flattened,   │                    │  automation halted,    │
│  orders cancelled,     │                    │  needs human           │
│  final PnL realized    │                    │  reconciliation        │
└───────────────────────┘                    └─────────────────────────┘
```

## What a grid ladder is

A grid ladder spans a price range (`range_low`–`range_high`) on one futures
symbol with an odd number of levels (`api/grid_ladders/calculations.py`).
Levels below the midpoint are buy (long) entries; levels above are sell
(short) entries. Each level's take-profit sits at the next level in, toward
the midpoint — so a buy at the low end takes profit at the midpoint, and a
sell at the high end also takes profit at the midpoint.

It's designed to profit from oscillation in ranging markets: a swing up
captures the short leg's round trip (sell high, buy back at the midpoint), a
swing down captures the long leg's (buy low, sell back at the midpoint) —
independent of which direction the market ultimately trends.

## The netting constraint

KuCoin futures has no hedge/dual-position mode — `positionSide` has exactly
one value, `BOTH`, documented by the exchange SDK as "one-way position", and
there is no way to tag an order as opening an independent long or short leg.
Every symbol carries a single net position.

That means the buy leg and the sell leg can never both be genuinely open at
the same time without the exchange netting them into one position — which
breaks the ladder's per-level bookkeeping if it isn't actively prevented.
`GridLadderLifecycle` (`api/grid_ladders/lifecycle.py`) enforces one rule:
**at most one side has live, unresolved exposure at any time.**

### Guard: pausing the opposite side

The moment a level's entry order fills, `_handle_filled_order` cancels every
still-resting entry order on the opposite side (`_cancel_side_entries`) before
placing this level's take-profit. The cancelled levels go back to `pending` —
not a terminal state, just "no live order right now."

Before cancelling, `_cancel_side_entries` re-checks each order's live exchange
state rather than trusting the local "still resting" status — that status can
be stale if the opposite order filled in the very same reconciliation tick.
If it finds a real fill there, it cancels nothing and reports back so the
caller can escalate instead of proceeding as if this side were alone.

### Re-arm: returning to flat

Once the live leg's take-profit fills, `_rearm_after_flat` re-arms that level
immediately (same-side levels never conflict with each other) and only re-arms
the paused opposite side once this side has no remaining live exposure at all.
Re-arming places a fresh entry order at the level's original price
(`_arm_level_entry`) — the same code path used for the ladder's initial
placement — after first clearing the level's prior round-trip state
(`reset_level_for_rearm`) so a stale `take_profit_order_id` from the previous
round can't block the next one. Levels are therefore repeatable: `realized_pnl`
accumulates across every round trip a level completes, not just the latest.

### Conflicting exposure: the escape hatch

Cancelling the opposite side's order can still race an in-flight fill on the
exchange — a standard cancel/match race, not fully eliminable without exchange
support. If both sides end up with real, unresolved exposure at once despite
the guard, `_handle_conflicting_exposure` marks both levels and the ladder
`error` and halts automation for that ladder (an `error`-status ladder is
untouched by `process_symbol`). This never tries to net or guess at the real
position — it surfaces the conflict for a human to reconcile against the
actual exchange state.

## Oscillation timeline

One full oscillation — at no point are both legs simultaneously exposed on
the exchange:

```
 t0            t1               t2              t3               t4
 │ both resting│ price↑ touches │ short entry    │ price↓ touches │ long entry
 │ buy@low      │ sell level     │ fills → guard: │ buy level      │ fills → guard:
 │ sell@high    │                │ cancel buy,    │ (re-armed at   │ cancel sell,
 │              │                │ place TP short │ t2's re-arm)   │ place TP long
 └──────────────┴────────────────┴────────────────┴────────────────┴──────────────
                                  │ TP fills       │                │ TP fills
                                  │ (mid) → re-arm │                │ (mid) → re-arm
                                  │ BOTH sides     │                │ BOTH sides
                                  ▼                                 ▼
                          short leg profit                   long leg profit
                          captured, flat again          captured, flat again
```

Whichever side isn't currently live has no resting order at all, so there's
nothing for KuCoin to net against the live leg — and once flat, both sides
come back up so the next oscillation, in either direction, is still caught.
