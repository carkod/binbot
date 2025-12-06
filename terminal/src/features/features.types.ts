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
export interface BenchmarkData {
  usdc: number[];
  btc: number[];
  dates: string[];
}

export interface BenchmarkSeriesData {
  usdcSeries: number[];
  btcSeries: number[];
  datesSeries: string[];
}

export interface BenchmarkCollection {
  benchmarkData: BenchmarkData;
  percentageSeries: BenchmarkSeriesData;
}
