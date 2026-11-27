export interface CandleClose {
  timestamp: number;
  close: number;
}

export const FIFTEEN_MINUTES_MS = 15 * 60 * 1000;

export const RISK_BETA_CANDLE_COUNT = 97;

const MIN_RETURNS = 20;

export function calculateRiskBeta(
  benchmarkCandles: CandleClose[],
  assetCandles: CandleClose[],
  completedBefore: number,
): number | null {
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

  const asset = completedCloses(assetCandles);

  const timestamps = [...benchmark.keys()]
    .filter((timestamp) => asset.has(timestamp))
    .sort((left, right) => left - right)
    .slice(-RISK_BETA_CANDLE_COUNT);

  if (timestamps.length < MIN_RETURNS + 1) return null;

  const assetReturns: number[] = [];

  const benchmarkReturns: number[] = [];

  let previousTimestamp: number | undefined;
  let previousAssetPrice: number | undefined;
  let previousBenchmark: number | undefined;

  for (const timestamp of timestamps) {
    const assetPrice = asset.get(timestamp)!;

    const benchmarkPrice = benchmark.get(timestamp)!;

    if (
      previousTimestamp === timestamp - FIFTEEN_MINUTES_MS &&
      previousAssetPrice !== undefined &&
      previousBenchmark !== undefined
    ) {
      assetReturns.push(assetPrice / previousAssetPrice - 1);
      benchmarkReturns.push(benchmarkPrice / previousBenchmark - 1);
    }
    previousTimestamp = timestamp;
    previousAssetPrice = assetPrice;
    previousBenchmark = benchmarkPrice;
  }

  const count = benchmarkReturns.length;

  if (count < MIN_RETURNS) return null;

  const benchmarkMean =
    benchmarkReturns.reduce((sum, value) => sum + value, 0) / count;

  const assetMean = assetReturns.reduce((sum, value) => sum + value, 0) / count;

  const variance = benchmarkReturns.reduce(
    (sum, value) => sum + (value - benchmarkMean) ** 2,
    0,
  );

  if (variance === 0) return null;

  const covariance = benchmarkReturns.reduce(
    (sum, value, index) =>
      sum + (value - benchmarkMean) * (assetReturns[index] - assetMean),
    0,
  );

  const beta = covariance / variance;

  return Number.isFinite(beta) ? beta : null;
}
