---
layout: default
title: Position lifecycle
---

# Position lifecycle architecture

The position lifecycle starts after an entry strategy has created and activated a
bot. Entry selection belongs to **binquant**; management of the open position
belongs to **binbot**.

This boundary keeps two different decisions separate:

- A binquant entry strategy decides **when to enter**, which symbol and direction
  to trade, and the initial bot parameters.
- A binbot lifecycle strategy decides **how an open position behaves**, including
  dynamic stop and trailing parameters, maximum holding time, reversal policy,
  and strategy-specific exits.

Lifecycle strategies describe intent. They do not place orders or write directly
to the database. `Lifecycle` applies their result through the shared execution
layer so exchange and persistence behaviour stays centralized.

## High-level flow

```mermaid
flowchart LR
    subgraph Binquant["binquant — entry"]
        Entry["strategies/&lt;path&gt;.py<br/>entry signal + ALGO"]
        Autotrade["consumers/autotrade_consumer.py<br/>autotrade gates"]
    end

    subgraph Bot["binbot — bot state"]
        Model["BotModel<br/>name = algorithm id"]
    end

    subgraph Streaming["binbot — open-position lifecycle"]
        Manager["streaming/position_manager.py<br/>market update"]
        Lifecycle["streaming/lifecycle.py<br/>orchestration"]
        Evaluator["streaming/context_evaluator.py<br/>resolve bot.name"]
        Strategy["streaming/strategies/&lt;path&gt;.py<br/>or default.py"]
        Execution["KucoinPositionDeal<br/>orders + persistence"]
    end

    Entry -->|"signal and bot parameters"| Autotrade
    Autotrade -->|"create and activate"| Model
    Model --> Manager
    Manager --> Lifecycle
    Lifecycle -->|"LifecycleContext"| Evaluator
    Evaluator -->|"selected strategy"| Strategy
    Strategy -->|"LifecyclePolicy + LifecycleSignal"| Lifecycle
    Lifecycle -->|"validated actions"| Execution
```

The algorithm id is the cross-repository contract. Binquant writes it to
`BotModel.name`; `LifecycleContextEvaluator` reads that name and selects the
registered lifecycle strategy.

## Entry-to-lifecycle matching contract

Every binquant entry strategy that can create a standard bot must have a
**deliberate lifecycle mapping** in binbot. There are two valid mappings:

1. A dedicated lifecycle strategy when the entry thesis needs custom management.
2. An explicit, tested decision to use `DefaultLifecycleStrategy` when the shared
   behaviour is sufficient.

Accidental fallback is not a lifecycle design. A new autotrading entry strategy
must not be enabled until its lifecycle mapping has been chosen and tested.

When a dedicated lifecycle strategy exists, it mirrors the binquant entry
strategy's relative path:

| Entry strategy in binquant | Lifecycle strategy in binbot |
| --- | --- |
| `strategies/mean_reversion_fade.py` | `streaming/strategies/mean_reversion_fade.py` |
| `strategies/coinrule/price_tracker.py` | `streaming/strategies/coinrule/price_tracker.py` |

The match has three parts:

- The files use the same relative strategy path and name.
- The binquant strategy's `ALGO` value matches one of the binbot lifecycle
  strategy's `algorithm_names` values exactly.
- The lifecycle class is included in `LifecycleContextEvaluator.STRATEGY_TYPES`.

The reverse rule also applies: every dedicated module under
`streaming/strategies/` must represent an existing binquant entry strategy.
Lifecycle-only strategy names and orphaned files should be removed.

The following files are framework code and do not need binquant counterparts:

- `streaming/strategies/base.py`
- `streaming/strategies/default.py`
- package `__init__.py` files

Grid ladders also sit outside this mapping because they use their own lifecycle
and persistence model rather than the standard bot lifecycle.

## File responsibilities

| File | Responsibility |
| --- | --- |
| `binquant/strategies/<path>.py` | Detects an entry and emits the stable algorithm id and initial bot parameters. |
| `binquant/consumers/autotrade_consumer.py` | Applies entry gates and creates or activates the bot through the binbot API. |
| `streaming/position_manager.py` | Receives a market update, loads the active bot, and starts a lifecycle tick. |
| `streaming/lifecycle.py` | Builds market context, applies strategy output, and owns the common position state machine. |
| `streaming/context_evaluator.py` | Resolves `BotModel.name` to a lifecycle strategy and contains strategy failures. |
| `streaming/strategies/base.py` | Defines the context, policy, signal, exit intent, and shared helpers. |
| `streaming/strategies/default.py` | Supplies common dynamic stop and trailing behaviour and is the intentional fallback. |
| `streaming/strategies/<path>.py` | Expresses only the lifecycle differences required by one entry strategy. |
| `api/exchange_apis/kucoin/futures/futures_deal.py` | Performs exchange operations and persists the resulting bot state. |
| `api/exchange_apis/kucoin/futures/position_sizing.py` | Increases futures quantity at trailing-profit triggers, reconciles fills, and disables increases when unaffordable without bypassing protective exits. |

### Top-gainer short chop exit

`top_gainer_short` counts completed candle closes switching sides of the fixed
current price over the rolling last six hours, using the shared
`pybinbot.shared.price_crossings.price_crossings_six_hours` calculation also used
by binquant. At **three or more crossings**, it closes the full live position
with a reduce-only **market order**, bypassing the normal IOC limit leg. This
exit runs before pending sizing recovery, new increases, and strategy parameter
changes. An already breached trailing stop still takes precedence.

This is a rolling history condition, not a six-hour minimum bot age. Wicks and
exact touches do not count; incomplete, stale, or invalid candle history does
not produce a chop exit. Normal protective stops continue to apply. The
binquant entry gate remains at four crossings; its score penalties are unchanged.
Release the updated shared `pybinbot` module before deploying these consumers.

## Dynamic position sizing

`BotBase.dynamic_position_sizing` defaults to `false`. For a KuCoin futures bot
with trailing enabled, it adds `deal.position_size_pct` percent of current
contracts only when `Lifecycle.exit()` reaches `deal.trailing_profit_price`.
The default increase is 25 percent, rounded down to exchange lots. Both long
and short positions use their existing trailing-profit direction.

Sizing does not own exits. Normal strategy evaluation, native stop-loss
protection, and full-position stops continue to run. A breach of
`deal.trailing_stop_loss_price`, including exact equality, closes the entire
exchange position before any sizing lookup or increase. There are no new
partial stop-loss reductions. Pending increases are disabled and open exchange
orders cancelled before a full close reads the live position quantity.

At a trailing-profit trigger, the lifecycle persists the next trigger and arms
or tightens its trailing stop. A confirmed increase updates weighted entry and
quantity without resetting those prices. The exchange trailing stop is resized
to cover the new full quantity even during replacement cooldowns, preserving
any tighter stop price. Restarting at the same price cannot repeat the increase.

The sizing class checks wallet affordability with `required_margin_for_contracts`
and the bot's persisted leverage. An unaffordable increase or a quantity below
one exchange lot disables sizing and clears fixed take profit while preserving
trailing protection. Fixed take-profit exits are bypassed while trailing-based
sizing remains enabled; `take_profit` does not define a separate sizing trigger.

`deal.position_size_order` persists an intent before submission. Recovery looks
up the original client ID, retains active orders until their terminal fills,
and retries missing increases with that same ID only after three missing-order
responses over 60 seconds. Pending lookups do not suppress normal exits. Old
reduction intents remain reconcilable but cannot be resubmitted. The legacy
`position_size_reference_price` no longer controls sizing thresholds.

The existing shared models and Alembic revision `a7b4e9c261f0` provide these
fields. No additional migration is needed. See
[dynamic position sizing](./bots/dynamic-position-sizing.md) for worked examples,
recovery details, and validation commands.

## Strategy input and output

`Lifecycle` builds one `LifecycleContext` for the current tick. It includes the
validated bot, current price, candle data, timing, Bollinger-band metrics,
current profit, and whether an exchange stop is live.

A lifecycle strategy returns a `LifecycleSignal` and exposes a
`LifecyclePolicy`:

- `LifecycleSignal.parameter_update` proposes stop-loss and trailing changes.
- `LifecycleSignal.exit_intent` requests an algorithmic close, such as a maximum
  holding-period exit.
- `LifecycleSignal.log_messages` explains decisions that should be persisted.
- `LifecyclePolicy` controls shared lifecycle branches such as low-price stop
  floors, emergency stop bounds, and reversal blocking.

`Lifecycle` remains responsible for applying those declarations in the correct
order. The strategy module must not call exchange APIs, mutate persistence, or
duplicate the common stop, trailing, and recovery state machine.

## Adding or changing an entry strategy

When an entry strategy is added or renamed:

1. Choose one stable algorithm id and preserve it from the binquant signal through
   `BotModel.name`.
2. Decide whether the standard lifecycle is sufficient.
3. If custom behaviour is required, add the matching relative module under
   `streaming/strategies/`, declare its `algorithm_names`, and register it in
   `LifecycleContextEvaluator.STRATEGY_TYPES`.
4. Add a resolution test plus focused tests for every custom policy, parameter
   update, and exit intent.
5. Check both repositories for orphaned entry or lifecycle names before enabling
   autotrade.

The intended result is a traceable pair: the entry thesis explains why a trade
was opened, and its lifecycle mapping explains how that trade will be managed
until it closes.
