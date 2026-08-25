import "@testing-library/jest-dom";
import { render, screen as rtlScreen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import {
  describe as describeBlock,
  expect as expectValue,
  it as testCase,
} from "vitest";
import { GridLadderStatus } from "../../../features/gridLadders/gridLadders";
import type { GridLadder } from "../../../features/gridLadders/gridLadders";
import GridLadderCard from "../GridLadderCard";

const ladder: GridLadder = {
  id: "ladder-1",
  symbol: "BTC-USDT",
  fiat: "USDT",
  exchange: "kucoin",
  market_type: "futures",
  algorithm_name: "grid_ladder",
  status: GridLadderStatus.ACTIVE,
  range_low: 90000,
  range_high: 100000,
  grid_step: 1000,
  level_count: 10,
  total_margin: 100,
  reserved_margin: 50,
  used_margin: 50,
  realized_pnl: 0,
  unrealized_pnl: 0,
  breakout_low: 89000,
  breakout_high: 101000,
  created_at: new Date(2026, 7, 25, 14, 30).getTime(),
  updated_at: new Date(2026, 7, 25, 14, 30).getTime(),
  context: {},
  levels: [],
  orders: [],
};

describeBlock("GridLadderCard", () => {
  testCase("shows the ladder entry timestamp", () => {
    render(
      <MemoryRouter>
        <GridLadderCard
          ladder={ladder}
          gridReturnPct={0}
          selected={false}
          onSelect={() => undefined}
          onClose={() => undefined}
          onDelete={() => undefined}
        />
      </MemoryRouter>,
    );

    expectValue(rtlScreen.getByText("Entry time")).toBeInTheDocument();
    expectValue(rtlScreen.getByText("25 Aug, 14:30")).toBeInTheDocument();
    expectValue(rtlScreen.queryByText("Exit time")).not.toBeInTheDocument();
  });

  testCase("shows the exit timestamp before total realized when closed", () => {
    render(
      <MemoryRouter>
        <GridLadderCard
          ladder={{
            ...ladder,
            status: GridLadderStatus.CLOSED,
            closed_at: new Date(2026, 7, 25, 16, 45).getTime(),
          }}
          gridReturnPct={0}
          selected={false}
          onSelect={() => undefined}
          onClose={() => undefined}
          onDelete={() => undefined}
        />
      </MemoryRouter>,
    );

    const exitTime = rtlScreen.getByText("Exit time");
    const totalRealized = rtlScreen.getByText("Total realized");

    expectValue(rtlScreen.getByText("25 Aug, 16:45")).toBeInTheDocument();
    expectValue(exitTime.closest(".row")?.nextElementSibling).toContainElement(
      totalRealized,
    );
  });
});
