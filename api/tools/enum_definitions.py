"""
Local enum definitions for Binbot.

These enums extend or replace pybinbot enums and serve as the canonical
source for the TypeScript frontend (terminal/src/utils/enums.ts is mostly
copied from here).
"""

from enum import Enum


class DealType(str, Enum):
    base_order = "base_order"
    take_profit = "take_profit"
    stop_loss = "stop_loss"
    short_sell = "short_sell"
    short_buy = "short_buy"
    margin_short = "margin_short"
    panic_close = "panic_close"
    trailling_profit = "trailling_profit"
    conversion = "conversion"
    algorithmic_close = "algorithmic_close"
