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
const btcCandles: CandleClose[] = Array.from({ length: 97 }, (_, index) => ({
  timestamp: (index + 3) * FIFTEEN_MINUTES_MS,
  close: 100 + index + (index % 3) * 2,
}));

describeBlock("BTC risk beta from completed 15-minute returns", () => {
  testCase(
    "a BTC-only holding has beta one and ignores a forming candle",
    () => {
      const formingCandle = {
        timestamp: completedBefore,
        close: 999999,
      };
      const result = calculateRiskBeta(
        [...btcCandles, formingCandle],
        [{ quantity: 1, candles: [...btcCandles, formingCandle] }],
        btcCandles.at(-1)!.close,
        completedBefore,
      );

      expectValue(result).toBe(1);
    },
  );

  testCase(
    "cash has zero beta and a short BTC position has negative beta",
    () => {
      expectValue(calculateRiskBeta(btcCandles, [], 200, completedBefore)).toBe(
        0,
      );
      expectValue(
        calculateRiskBeta(
          btcCandles,
          [{ quantity: -1, candles: btcCandles }],
          300,
          completedBefore,
        ),
      ).toBeLessThan(0);
    },
  );

  testCase(
    "requires aligned, consecutive candles with benchmark variance",
    () => {
      const shiftedCandles = btcCandles.map(({ timestamp, close }) => ({
        timestamp: timestamp + 60_000,
        close,
      }));
      expectValue(
        calculateRiskBeta(
          btcCandles,
          [{ quantity: 1, candles: shiftedCandles }],
          200,
          completedBefore,
        ),
      ).toBeNull();
      expectValue(
        calculateRiskBeta(
          btcCandles.map((candle) => ({ ...candle, close: 100 })),
          [],
          200,
          completedBefore,
        ),
      ).toBeNull();
    },
  );
});
