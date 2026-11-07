export interface CandleClose {
  timestamp: number;
  close: number;
}

export interface RiskExposure {
  quantity: number;
  candles: CandleClose[];
}

export const FIFTEEN_MINUTES_MS = 15 * 60 * 1000;
export const RISK_BETA_CANDLE_COUNT = 97;
const MIN_RETURNS = 20;

export function calculateRiskBeta(
  benchmarkCandles: CandleClose[],
  exposures: RiskExposure[],
  accountValue: number,
  completedBefore: number,
): number | null {
  if (!Number.isFinite(accountValue) || accountValue <= 0) return null;

  const completedCloses = (candles: CandleClose[]) =>
    new Map(
      candles
        .filter(
          ({ timestamp, close }) =>
            Number.isFinite(timestamp) &&
            timestamp % FIFTEEN_MINUTES_MS === 0 &&
            timestamp + FIFTEEN_MINUTES_MS <= completedBefore &&
            Number.isFinite(close) &&
            close > 0,
        )
        .map(({ timestamp, close }) => [timestamp, close] as const),
    );

  const benchmark = completedCloses(benchmarkCandles);
  const prices = exposures.map(({ candles }) => completedCloses(candles));
  const timestamps = [...benchmark.keys()]
    .filter((timestamp) => prices.every((series) => series.has(timestamp)))
    .sort((left, right) => left - right)
    .slice(-RISK_BETA_CANDLE_COUNT);

  if (timestamps.length < MIN_RETURNS + 1) return null;

  const latest = timestamps[timestamps.length - 1];
  const latestPrices = prices.map((series) => series.get(latest)!);
  const portfolioReturns: number[] = [];
  const benchmarkReturns: number[] = [];
  let previousTimestamp: number | undefined;
  let previousValue: number | undefined;
  let previousBenchmark: number | undefined;

  for (const timestamp of timestamps) {
    const value =
      accountValue +
      exposures.reduce(
        (change, exposure, index) =>
          change +
          exposure.quantity *
            (prices[index].get(timestamp)! - latestPrices[index]),
        0,
      );
    if (value <= 0) return null;

    const benchmarkPrice = benchmark.get(timestamp)!;
    if (
      previousTimestamp === timestamp - FIFTEEN_MINUTES_MS &&
      previousValue !== undefined &&
      previousBenchmark !== undefined
    ) {
      portfolioReturns.push(value / previousValue - 1);
      benchmarkReturns.push(benchmarkPrice / previousBenchmark - 1);
    }
    previousTimestamp = timestamp;
    previousValue = value;
    previousBenchmark = benchmarkPrice;
  }

  const count = benchmarkReturns.length;
  if (count < MIN_RETURNS) return null;
  const benchmarkMean =
    benchmarkReturns.reduce((sum, value) => sum + value, 0) / count;
  const portfolioMean =
    portfolioReturns.reduce((sum, value) => sum + value, 0) / count;
  const variance = benchmarkReturns.reduce(
    (sum, value) => sum + (value - benchmarkMean) ** 2,
    0,
  );
  if (variance === 0) return null;

  const covariance = benchmarkReturns.reduce(
    (sum, value, index) =>
      sum + (value - benchmarkMean) * (portfolioReturns[index] - portfolioMean),
    0,
  );
  return Math.round((covariance / variance) * 10000) / 10000;
}
