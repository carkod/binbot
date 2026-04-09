interface AssetCollection {
  [asset: string]: number;
}

export interface BalanceData {
  balances: AssetCollection;
  fiat_available: number;
  fiat_currency: number;
  estimated_total_fiat: number;
}

// Benchmark of portfolio (in USDC at time of writing) against BTC
export interface BenchmarkSeries {
  fiat: number[];
  btc: number[];
  dates: string[];
}

interface BenchmarkStats {
  sharpe: number;
  pnl: number;
}

export interface BenchmarkSeriesData {
  fiatSeries: number[];
  btcSeries: number[];
  datesSeries: string[];
}

export interface BenchmarkCollection {
  benchmarkData: BenchmarkSeries;
  percentageSeries: BenchmarkSeriesData;
  portfolioStats: BenchmarkStats;
}
