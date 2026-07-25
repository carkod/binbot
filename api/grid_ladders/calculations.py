from dataclasses import dataclass

from api.grid_ladders.sizing import GridMarginSizer, round_price_to_precision


@dataclass(frozen=True)
class CalculatedGridLevel:
    level_index: int
    price: float
    side: str
    contracts: int
    margin_required: float
    take_profit_price: float | None


@dataclass(frozen=True)
class CalculatedGrid:
    grid_step: float
    levels: list[CalculatedGridLevel]
    logs: list[str]


def calculate_grid_step(range_low: float, range_high: float, level_count: int) -> float:
    return (range_high - range_low) / (level_count - 1)


def calculate_grid_levels(
    range_low: float,
    range_high: float,
    level_count: int,
    total_margin: float,
    sizer: GridMarginSizer,
    *,
    allowed_entry_sides: set[str] | None = None,
    min_entry_contracts: int = 1,
) -> CalculatedGrid:
    grid_step = calculate_grid_step(range_low, range_high, level_count)
    midpoint_index = level_count // 2
    active_entry_level_count = 0
    for level_index in range(level_count):
        if level_index < midpoint_index:
            side = "buy"
        elif level_index > midpoint_index:
            side = "sell"
        else:
            side = "neutral"
        if side != "neutral" and (
            allowed_entry_sides is None or side in allowed_entry_sides
        ):
            active_entry_level_count += 1
    if active_entry_level_count == 0:
        raise ValueError("Grid has no active entry levels")

    per_level_margin = total_margin / active_entry_level_count
    prices = [
        round_price_to_precision(range_low + (grid_step * index), sizer.price_precision)
        for index in range(level_count)
    ]
    if len(set(prices)) != len(prices):
        raise ValueError(
            "Grid levels collapse after symbol price precision rounding; "
            "widen the range or reduce level_count"
        )
    levels: list[CalculatedGridLevel] = []
    logs: list[str] = []

    for level_index in range(level_count):
        price = prices[level_index]
        if level_index < midpoint_index:
            side = "buy"
            take_profit_price = prices[level_index + 1]
        elif level_index > midpoint_index:
            side = "sell"
            take_profit_price = prices[level_index - 1]
        else:
            side = "neutral"
            take_profit_price = None

        if side != "neutral" and allowed_entry_sides is not None:
            if side not in allowed_entry_sides:
                side = "neutral"
                take_profit_price = None

        contracts = 0
        margin_required = 0.0
        if side != "neutral":
            contracts = sizer.max_contracts_for_margin(per_level_margin, price)
            if contracts == 0:
                logs.append(
                    f"Grid level {level_index} cannot afford the exchange minimum contract size; "
                    "level disabled"
                )
                side = "neutral"
                take_profit_price = None
            elif contracts < min_entry_contracts:
                logs.append(
                    f"Grid level {level_index} calculated {contracts} contract; "
                    f"requires at least {min_entry_contracts} contracts; level disabled"
                )
                contracts = 0
                side = "neutral"
                take_profit_price = None
            else:
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

    return CalculatedGrid(grid_step=grid_step, levels=levels, logs=logs)
