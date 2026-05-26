import {
  GridLadderStatus,
  type GridLadder,
} from "../features/gridLadders/gridLadders";
import {
  calculateGridLivePnl,
  calculateGridLiveReturnPct,
  calculateGridLiveUnrealizedPnl,
} from "./grid-ladder";

const makeLadder = (overrides: Partial<GridLadder> = {}): GridLadder => ({
  id: "ladder-1",
  symbol: "QNTUSDTM",
  fiat: "USDT",
  exchange: "kucoin",
  market_type: "FUTURES",
  algorithm_name: "fixed_grid",
  status: GridLadderStatus.ACTIVE,
  range_low: 70,
  range_high: 80,
  grid_step: 1,
  level_count: 3,
  total_margin: 100,
  reserved_margin: 100,
  used_margin: 50,
  realized_pnl: 0,
  unrealized_pnl: 0.21,
  breakout_low: 69,
  breakout_high: 81,
  created_at: 1,
  updated_at: 1,
  context: {},
  levels: [],
  orders: [],
  ...overrides,
});

describe("grid ladder live PnL", () => {
  it("uses the KuCoin contract multiplier when estimating unrealized PnL", () => {
    const ladder = makeLadder({
      levels: [
        {
          id: "level-1",
          ladder_id: "ladder-1",
          level_index: 0,
          price: 75,
          side: "buy",
          contracts: 100,
          margin_required: 75,
          status: "take_profit_open",
          entry_order_id: "entry-1",
          take_profit_order_id: "tp-1",
          filled_entry_price: 75,
          filled_entry_qty: 100,
          take_profit_price: 76,
          realized_pnl: 0,
          created_at: 1,
          updated_at: 1,
        },
      ],
    });

    expect(calculateGridLiveUnrealizedPnl(ladder, 76, 0.01)).toBe(1);
  });

  it("does not count open entry orders as unrealized positions", () => {
    const ladder = makeLadder({
      levels: [
        {
          id: "level-1",
          ladder_id: "ladder-1",
          level_index: 0,
          price: 75,
          side: "buy",
          contracts: 100,
          margin_required: 75,
          status: "open",
          entry_order_id: "entry-1",
          take_profit_order_id: null,
          filled_entry_price: null,
          filled_entry_qty: 0,
          take_profit_price: 76,
          realized_pnl: 0,
          created_at: 1,
          updated_at: 1,
        },
      ],
    });

    expect(calculateGridLiveUnrealizedPnl(ladder, 76, 0.01)).toBe(0);
  });

  it("combines active level cycles with live unrealized PnL for return pct", () => {
    const ladder = makeLadder({
      total_margin: 100,
      levels: [
        {
          id: "level-1",
          ladder_id: "ladder-1",
          level_index: 0,
          price: 75,
          side: "buy",
          contracts: 100,
          margin_required: 75,
          status: "completed",
          entry_order_id: "entry-1",
          take_profit_order_id: "tp-1",
          filled_entry_price: 75,
          filled_entry_qty: 100,
          take_profit_price: 76,
          realized_pnl: 0.5,
          created_at: 1,
          updated_at: 1,
        },
      ],
    });

    expect(calculateGridLivePnl(ladder, 0.25)).toBe(0.75);
    expect(calculateGridLiveReturnPct(ladder, 0.25)).toBe(0.75);
  });
});
