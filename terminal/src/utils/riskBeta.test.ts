import {
  describe as describeBlock,
  expect as expectValue,
  it as testCase,
} from "vitest";
import {
  calculateRiskBeta,
  FIFTEEN_MINUTES_MS,
  type CandleClose,
} from "./riskBeta";

const completedBefore = 100 * FIFTEEN_MINUTES_MS;

function candlesWithBeta(beta: number): CandleClose[] {
  let close = 100;

  return Array.from({ length: 97 }, (_, index) => {
    if (index > 0) close *= 1 + beta * [0.01, -0.02, 0.02, -0.01][index % 4];
    return { timestamp: (index + 3) * FIFTEEN_MINUTES_MS, close };
  });
}

const btcCandles = candlesWithBeta(1);

describeBlock(
  "symbol beta against BTC from completed 15-minute returns",
  () => {
    testCase.each([1, 1.5, -2, 0])(
      "calculates beta %s from the asset's own returns",
      (beta) => {
        expectValue(
          calculateRiskBeta(btcCandles, candlesWithBeta(beta), completedBefore),
        ).toBeCloseTo(beta, 10);
      },
    );

    testCase("excludes a forming candle from both series", () => {
      expectValue(
        calculateRiskBeta(
          [...btcCandles, { timestamp: completedBefore, close: 999999 }],
          [...candlesWithBeta(1.5), { timestamp: completedBefore, close: 1 }],
          completedBefore,
        ),
      ).toBeCloseTo(1.5, 10);
    });

    testCase(
      "sorts candles and uses only matching consecutive intervals",
      () => {
        const asset = candlesWithBeta(1.5).filter((_, index) => index !== 50);

        expectValue(
          calculateRiskBeta([...btcCandles].reverse(), asset, completedBefore),
        ).toBeCloseTo(1.5, 10);
      },
    );

    testCase("requires at least twenty aligned returns", () => {
      expectValue(
        calculateRiskBeta(btcCandles, btcCandles.slice(-20), completedBefore),
      ).toBeNull();
      expectValue(
        calculateRiskBeta(btcCandles, btcCandles.slice(-21), completedBefore),
      ).toBe(1);
    });

    testCase(
      "returns unavailable for misaligned candles or a flat benchmark",
      () => {
        expectValue(
          calculateRiskBeta(
            btcCandles,
            btcCandles.map((candle) => ({
              ...candle,
              timestamp: candle.timestamp + 60000,
            })),
            completedBefore,
          ),
        ).toBeNull();
        expectValue(
          calculateRiskBeta(candlesWithBeta(0), btcCandles, completedBefore),
        ).toBeNull();
      },
    );
  },
);
