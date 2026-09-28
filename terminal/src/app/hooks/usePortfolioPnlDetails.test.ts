import { renderHook } from "@testing-library/react";
import type {
  BalanceData,
  BenchmarkCollection,
} from "../../features/features.types";
import { usePortfolioPnlDetails } from "./usePortfolioPnlDetails";

const accountData: BalanceData = {
  balances: {},
  fiat_available: 20,
  fiat_currency: "USDC",
  estimated_total_fiat: 110,
  total_deposit: 5,
};

const benchmark: BenchmarkCollection = {
  benchmarkData: {
    fiat: [100, 105],
    btc: [70_000, 71_000],
    dates: ["2026-09-26", "2026-09-27"],
  },
  percentageSeries: {
    fiatSeries: [],
    btcSeries: [],
    datesSeries: [],
  },
  portfolioStats: {
    pnl: 0,
    sharpe: 0,
    btc_sharpe: 0,
  },
};

describe("usePortfolioPnlDetails", () => {
  it("compares the live portfolio value with the previous stored value", () => {
    const { result } = renderHook(() =>
      usePortfolioPnlDetails(benchmark, accountData),
    );

    expect(result.current.portfolioPnlValue).toBe(5);
    expect(result.current.portfolioPnlPercentage).toBeCloseTo(4.76, 2);
    expect(result.current.portfolioPnlClass).toBe("text-success");
  });

  it("returns empty details while its inputs are unavailable", () => {
    const { result } = renderHook(() => usePortfolioPnlDetails());

    expect(result.current).toEqual({
      portfolioPnlValue: undefined,
      portfolioPnlPercentage: undefined,
      portfolioPnlClass: "",
    });
  });
});
