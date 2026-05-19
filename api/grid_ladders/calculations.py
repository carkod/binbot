from dataclasses import dataclass

from grid_ladders.sizing import GridMarginSizer


@dataclass(frozen=True)
class CalculatedGridLevel:
    level_index: int
    price: float
    side: str
    contracts: int
    margin_required: float
    take_profit_price: float | None


def calculate_grid_step(range_low: float, range_high: float, level_count: int) -> float:
    return (range_high - range_low) / (level_count - 1)


def calculate_grid_levels(
    range_low: float,
    range_high: float,
    level_count: int,
    total_margin: float,
    sizer: GridMarginSizer,
) -> list[CalculatedGridLevel]:
    grid_step = calculate_grid_step(range_low, range_high, level_count)
    midpoint_index = level_count // 2
    active_entry_level_count = level_count - 1
    per_level_margin = total_margin / active_entry_level_count
    levels: list[CalculatedGridLevel] = []

    for level_index in range(level_count):
        price = range_low + (grid_step * level_index)
        if level_index < midpoint_index:
            side = "buy"
            take_profit_price = price + grid_step
        elif level_index > midpoint_index:
            side = "sell"
            take_profit_price = price - grid_step
        else:
            side = "neutral"
            take_profit_price = None

        contracts = 0
        margin_required = 0.0
        if side != "neutral":
            contracts = sizer.max_contracts_for_margin(per_level_margin, price)
            if contracts == 0:
                raise ValueError(
                    f"Grid level {level_index} cannot afford the exchange minimum contract size"
                )
            margin_required = sizer.required_margin_for_contracts(contracts, price)

        levels.append(
            CalculatedGridLevel(
                level_index=level_index,
                price=price,
                side=side,
                contracts=contracts,
                margin_required=margin_required,
                take_profit_price=take_profit_price,
            )
        )

    return levels
