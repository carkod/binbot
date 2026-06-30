# Code Practices

This repository favors direct, explicit code over thin indirection.

## Workspace Map

This VS Code workspace spans several connected projects. When discussing or changing code, keep the project boundary clear:

- `~/binbot/api` is the **binbot FastAPI app**. It owns the API, database models, CRUD layer, exchange integrations, and backend trading execution behavior.
- `~/binbot/terminal` is the **binbot React dashboard app**. It is the operational UI for bots, symbols, account state, and API-driven workflows.
- `~/binquant` is the **crypto analytics, bot update, and signal system**. It produces and analyzes strategy signals, live bot updates, and performance context that can feed into binbot workflows.
- `pybinbot` is the **shared PyPI module** used by both `~/binquant` and `~/binbot/api`. Shared models, clients, and reusable domain modules belong here when they genuinely need to be consumed by both projects.
- `~/binbot.in` is the **brochure site**, a Next.js app for the public-facing website rather than the trading operations product.

These projects are interconnected, and Codex conversations often refer across them. Prefer naming the project or path explicitly when a change crosses boundaries, especially when touching shared contracts between `binbot/api`, `binbot/terminal`, `binquant`, and `pybinbot`.

## Function Shape

- When making technical decisions, do not give much weight to development cost.
- Do not add wrapper methods whose only job is to pass instance state into another method.
- Prefer one clearly named function with explicit parameters over a public method that delegates to a private method with the real logic.
- If a helper is needed, it should remove meaningful duplication or isolate a distinct concept, not just rename the same operation.
- Avoid functions that return another function unless the returned callable is the actual domain concept being modeled.
- Keep method names aligned with what callers want to do. For example, `calculate_contracts(balance, price)` should calculate contracts directly.

## Imports

- Prefer specific imports for the functions, classes, or constants being used, such as `from databases.utils import get_db_session`, over importing broader modules when only a few names are needed.

## Trading Logic

- For KuCoin futures bots, `fiat_order_size` is the **initial margin** the bot commits (margin-spend interpretation), not the risk-at-stop. `KucoinPositionDeal.calculate_contracts(balance, price)` is `balance * symbol_info.futures_leverage / (price * multiplier)`; `contracts_to_fiat_order_size` is its inverse. `notional = fiat_order_size * futures_leverage`.
- Leverage lives on the symbol row (`SymbolTable.futures_leverage`, bounded `[1, 5]`). It is **per-symbol**, not a global constant. New symbols default to `1x`; dial individual symbols up via the symbols API only as an explicit product decision.
- `base_order` clamps via `min(margin_sized_contracts, max_contracts_for_margin(available_balance, price))` and re-validates with `required_margin_for_contracts` before sending the order to KuCoin. Anything that places futures orders must keep going through `required_margin_for_contracts` so the affordability check stays exchange-truthful.
- Percent fields stored as values like `6.5` must be converted to ratios with `/ 100` before arithmetic.
- Do not apply leverage to PnL or risk-at-stop calculations. Leverage affects margin requirements, not the price move loss for a position.
- Keep exchange-specific assumptions near the exchange implementation and cover them with focused tests.

## Model Fields

- Trust Pydantic model defaults and types for fields such as `active_bot.*` and `active_bot.deal.*`.
- Do not add fallback expressions like `self.active_bot.deal.stop_loss_price or 0` when the model already defines `0` as the default.
- Do not wrap model fields in casts like `float(...)` when the Pydantic model already validates the field as a float.
- Use validated bot fields directly in trading arithmetic and comparisons, for example `self.active_bot.deal.trailing_stop_loss_price`, `self.active_bot.deal.opening_price`, `self.active_bot.stop_loss`, and `self.active_bot.trailing_profit`.
- Do not write patterns such as `float(self.active_bot.deal.trailing_stop_loss_price or 0)`, `float(self.active_bot.stop_loss)`, or `int(self.active_bot.deal.opening_timestamp)` for validated Pydantic model fields.
- Add explicit fallbacks or casts only at real trust boundaries, such as raw exchange payloads, database rows before validation, or optional third-party values.

## Tests

- Add small regression tests for sizing, rounding, stop placement, and reversal logic whenever those calculations change.
- Prefer tests that name the business rule being protected, especially for trading risk behavior.
- Run `make format` from `api/` to check formatting, linting, and mypy.
- Run `make test` from `api/` to run pytest.
