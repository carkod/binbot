from dataclasses import dataclass
from collections.abc import Sequence

from databases.tables.grid_ladder_table import GridLadderTable

MAX_ACTIVE_LADDERS_DEFAULT = 2
MAX_ACTIVE_LADDERS_HARD = 3
GRID_ALLOCATION_PCT = 1.0
CASH_RESERVE_PCT = 0.0
MAX_MARGIN_PER_LADDER_PCT = 0.25


@dataclass(frozen=True)
class GridCapitalDecision:
    active_ladder_count: int
    reserved_grid_margin: float
    available_after_cash_reserve: float
    allowed_grid_margin: float
    allowed_margin_for_new_ladder: float


def evaluate_grid_capital(
    active_ladders: Sequence[GridLadderTable],
    available_fiat_balance: float,
    requested_margin: float,
    max_active_ladders: int = MAX_ACTIVE_LADDERS_DEFAULT,
) -> GridCapitalDecision:
    if max_active_ladders > MAX_ACTIVE_LADDERS_HARD:
        raise ValueError("max_active_ladders cannot exceed the hard maximum of 3")

    active_ladder_count = len(active_ladders)
    if active_ladder_count >= max_active_ladders:
        raise ValueError(
            f"Grid ladder limit reached: max_active_ladders={max_active_ladders}"
        )

    reserved_grid_margin = sum(ladder.reserved_margin for ladder in active_ladders)
    available_after_cash_reserve = available_fiat_balance * (1 - CASH_RESERVE_PCT)
    allowed_grid_margin = available_fiat_balance * GRID_ALLOCATION_PCT
    remaining_grid_margin = max(allowed_grid_margin - reserved_grid_margin, 0)
    per_ladder_cap = available_fiat_balance * MAX_MARGIN_PER_LADDER_PCT
    allowed_margin_for_new_ladder = min(
        available_after_cash_reserve,
        remaining_grid_margin,
        per_ladder_cap,
    )

    if requested_margin > allowed_margin_for_new_ladder:
        raise ValueError(
            f"Grid ladder margin {requested_margin} exceeds allowed margin {allowed_margin_for_new_ladder}"
        )

    return GridCapitalDecision(
        active_ladder_count=active_ladder_count,
        reserved_grid_margin=reserved_grid_margin,
        available_after_cash_reserve=available_after_cash_reserve,
        allowed_grid_margin=allowed_grid_margin,
        allowed_margin_for_new_ladder=allowed_margin_for_new_ladder,
    )
