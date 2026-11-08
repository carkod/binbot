import {
  afterEach as afterEachTest,
  describe as describeBlock,
  expect as expectValue,
  it as testCase,
  vi,
} from "vitest";
import { ExchangeId } from "../../utils/enums";
import { loadCandles } from "./useRiskBeta";

const completedBefore = 1_710_000_900_000;
const signal = new AbortController().signal;

describeBlock("15-minute beta candle requests", () => {
  afterEachTest(() => vi.unstubAllGlobals());

  testCase("reads Binance's close at index four", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => [[completedBefore - 900_000, "1", "2", "0", "105"]],
    });
    vi.stubGlobal("fetch", fetchMock);

    const candles = await loadCandles(
      "BTCUSDT",
      ExchangeId.BINANCE,
      completedBefore,
      signal,
    );

    expectValue(candles).toEqual([
      { timestamp: completedBefore - 900_000, close: 105 },
    ]);
    expectValue(fetchMock.mock.calls[0][0]).toContain("interval=15m");
    expectValue(fetchMock.mock.calls[0][0]).toContain("symbol=BTCUSDT");
  });

  testCase(
    "reads KuCoin spot's seconds timestamp and close at index two",
    async () => {
      const fetchMock = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          data: [
            [String((completedBefore - 900_000) / 1000), "1", "106", "2", "0"],
          ],
        }),
      });
      vi.stubGlobal("fetch", fetchMock);

      const candles = await loadCandles(
        "BTC-USDT",
        ExchangeId.KUCOIN,
        completedBefore,
        signal,
      );

      expectValue(candles).toEqual([
        { timestamp: completedBefore - 900_000, close: 106 },
      ]);
      expectValue(fetchMock.mock.calls[0][0]).toContain("type=15min");
    },
  );

  testCase("requests 15-minute KuCoin futures candles", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        data: [[completedBefore - 900_000, "1", "2", "0", "107"]],
      }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const candles = await loadCandles(
      "XBTUSDTM",
      ExchangeId.KUCOIN,
      completedBefore,
      signal,
      true,
    );

    expectValue(candles).toEqual([
      { timestamp: completedBefore - 900_000, close: 107 },
    ]);
    expectValue(fetchMock.mock.calls[0][0]).toContain("granularity=15");
  });
});
