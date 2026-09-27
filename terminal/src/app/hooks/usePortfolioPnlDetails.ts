import type {
  BalanceData,
  BenchmarkCollection,
} from "../../features/features.types";

export type PortfolioPnlDetails = {
  portfolioPnlValue: number | undefined;
  portfolioPnlPercentage: number | undefined;
  portfolioPnlClass: string;
};

export const usePortfolioPnlDetails = (
  benchmark?: BenchmarkCollection,
  accountData?: BalanceData,
): PortfolioPnlDetails => {
  const benchmarkSeries = benchmark?.benchmarkData?.fiat;
  const latestPortfolioValue =
    accountData?.estimated_total_fiat !== undefined
      ? accountData.estimated_total_fiat - (accountData.total_deposit ?? 0)
      : undefined;
  const lastBenchmarkValue = benchmarkSeries?.[benchmarkSeries.length - 1];
  const previousStoredPortfolioValue =
    benchmarkSeries && benchmarkSeries.length > 1
      ? benchmarkSeries[benchmarkSeries.length - 2]
      : lastBenchmarkValue;
  const previousPortfolioValue =
    latestPortfolioValue !== undefined &&
    lastBenchmarkValue !== undefined &&
    Math.abs(lastBenchmarkValue - latestPortfolioValue) < 0.0001
      ? previousStoredPortfolioValue
      : lastBenchmarkValue;
  const portfolioPnlValue =
    latestPortfolioValue !== undefined && previousPortfolioValue !== undefined
      ? latestPortfolioValue - previousPortfolioValue
      : undefined;
  const portfolioPnlPercentage =
    portfolioPnlValue !== undefined && latestPortfolioValue
      ? (portfolioPnlValue / latestPortfolioValue) * 100
      : undefined;
  const portfolioPnlClass =
    portfolioPnlValue === undefined
      ? ""
      : portfolioPnlValue > 0
        ? "text-success"
        : "text-danger";

  return {
    portfolioPnlValue,
    portfolioPnlPercentage,
    portfolioPnlClass,
  };
};
