import "@testing-library/jest-dom";
import { render, screen as rtlScreen } from "@testing-library/react";
import {
  describe as describeBlock,
  expect as expectValue,
  it as testCase,
  vi,
} from "vitest";
import { MarketType } from "../../../utils/enums";

const useRiskBeta = vi.hoisted(() => vi.fn());

vi.mock("../../hooks/useRiskBeta", () => ({
  useRiskBeta,
}));

import BalanceAnalysis from "../BalanceAnalysis";

const accountData = {
  balances: { BTC: 1, USDT: 100 },
  fiat_available: 100,
  fiat_currency: "USDT",
  estimated_total_fiat: 200,
  total_deposit: 0,
};

describeBlock("BalanceAnalysis risk beta", () => {
  testCase("shows BTC beta calculated from 15-minute spot returns", () => {
    useRiskBeta.mockReturnValue({
      beta: 0.4567,
      isLoading: false,
    });

    render(
      <BalanceAnalysis
        accountData={accountData}
        marketType={MarketType.SPOT}
      />,
    );

    expectValue(rtlScreen.getByText("Risk beta (BTC)")).toBeInTheDocument();
    expectValue(rtlScreen.getByText("0.46")).toBeInTheDocument();
    expectValue(useRiskBeta).toHaveBeenCalledWith(accountData, MarketType.SPOT);
  });

  testCase("shows beta for live futures positions", () => {
    useRiskBeta.mockReturnValue({
      beta: -1.2345,
      isLoading: false,
    });

    render(
      <BalanceAnalysis
        accountData={accountData}
        marketType={MarketType.FUTURES}
      />,
    );

    expectValue(rtlScreen.getByText("-1.23")).toBeInTheDocument();
    expectValue(useRiskBeta).toHaveBeenCalledWith(
      accountData,
      MarketType.FUTURES,
    );
  });
});
