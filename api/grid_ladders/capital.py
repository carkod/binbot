from collections.abc import Sequence
from dataclasses import dataclass

from api.databases.crud.autotrade_crud import AutotradeCrud
from api.databases.tables.grid_ladder_table import GridLadderTable
from sqlmodel import Session


@dataclass(frozen=True)
class GridCapitalDecision:
    active_ladder_count: int
    reserved_grid_margin: float
    available_after_cash_reserve: float
    allowed_grid_margin: float
    allowed_margin_for_new_ladder: float


class GridCapitalSettings:
    # Per-ladder margin cap as a fraction of available balance. Not yet in
    # autotrade settings; stored here until a settings field is added.
    MAX_MARGIN_PER_LADDER_PCT = 0.25

    def __init__(self, session: Session | None = None) -> None:
        settings = AutotradeCrud(session).get_settings()
        self.max_active_ladders: int = settings.grid_max_active_ladders
        self.grid_allocation_pct: float = settings.grid_allocation_pct
        self.cash_reserve_pct: float = settings.grid_cash_reserve_pct

    def evaluate_grid_capital(
        self,
        active_ladders: Sequence[GridLadderTable],
        available_fiat_balance: float,
        requested_margin: float,
    ) -> GridCapitalDecision:
        active_ladder_count = len(active_ladders)
        if active_ladder_count >= self.max_active_ladders:
            raise ValueError(
                f"Grid ladder limit reached: max_active_ladders={self.max_active_ladders}"
            )

        reserved_grid_margin = sum(ladder.reserved_margin for ladder in active_ladders)
        available_after_cash_reserve = available_fiat_balance * (
            1 - self.cash_reserve_pct
        )
        allowed_grid_margin = available_fiat_balance * self.grid_allocation_pct
        remaining_grid_margin = max(allowed_grid_margin - reserved_grid_margin, 0)
        per_ladder_cap = available_fiat_balance * self.MAX_MARGIN_PER_LADDER_PCT
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
