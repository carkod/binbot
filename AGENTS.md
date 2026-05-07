# Code Practices

This repository favors direct, explicit code over thin indirection.

## Function Shape

- Do not add wrapper methods whose only job is to pass instance state into another method.
- Prefer one clearly named function with explicit parameters over a public method that delegates to a private method with the real logic.
- If a helper is needed, it should remove meaningful duplication or isolate a distinct concept, not just rename the same operation.
- Avoid functions that return another function unless the returned callable is the actual domain concept being modeled.
- Keep method names aligned with what callers want to do. For example, `calculate_contracts(balance, price)` should calculate contracts directly.

## Trading Logic

- Treat futures sizing carefully: `fiat_order_size` is the configured risk budget unless surrounding code explicitly documents a margin-spend interpretation.
- Percent fields stored as values like `6.5` must be converted to ratios with `/ 100` before arithmetic.
- Do not apply leverage to PnL or risk-at-stop calculations. Leverage affects margin requirements, not the price move loss for a position.
- Use `1x` leverage for KuCoin futures orders unless a later product decision explicitly changes this.
- Keep exchange-specific assumptions near the exchange implementation and cover them with focused tests.

## Model Fields

- Trust Pydantic model defaults and types for fields such as `active_bot.*` and `active_bot.deal.*`.
- Do not add fallback expressions like `self.active_bot.deal.stop_loss_price or 0` when the model already defines `0` as the default.
- Do not wrap model fields in casts like `float(...)` when the Pydantic model already validates the field as a float.
- Add explicit fallbacks or casts only at real trust boundaries, such as raw exchange payloads, database rows before validation, or optional third-party values.

## Tests

- Add small regression tests for sizing, rounding, stop placement, and reversal logic whenever those calculations change.
- Prefer tests that name the business rule being protected, especially for trading risk behavior.
