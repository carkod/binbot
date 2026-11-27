import { act, renderHook, waitFor } from "@testing-library/react";
import {
  afterEach as afterEachTest,
  beforeEach as beforeEachTest,
  describe as describeBlock,
  expect as expectValue,
  it as testCase,
  vi,
} from "vitest";
import { ExchangeId, MarketType } from "../../utils/enums";
import { FIFTEEN_MINUTES_MS } from "../../utils/riskBeta";
import { loadCandles, useRiskBeta } from "./useRiskBeta";

const useGetSettingsQuery = vi.hoisted(() => vi.fn());

vi.mock("../../features/autotradeApiSlice", () => ({
  useGetSettingsQuery,
}));

const completedBefore = 1_710_000_900_000;

const signal = new AbortController().signal;

afterEachTest(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describeBlock("15-minute beta candle requests", () => {
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

describeBlock("selected symbol beta", () => {
  function futuresRows(beta: number) {
    let close = 100;

    return Array.from({ length: 97 }, (_, index) => {
      if (index > 0) close *= 1 + beta * [0.01, -0.02, 0.02, -0.01][index % 4];
      return [
        completedBefore - (97 - index) * FIFTEEN_MINUTES_MS,
        0,
        0,
        0,
        close,
      ];
    });
  }

  const response = (beta: number) => ({
    ok: true,
    json: async () => ({ data: futuresRows(beta) }),
  });

  beforeEachTest(() => {
    vi.spyOn(Date, "now").mockReturnValue(completedBefore);
    useGetSettingsQuery.mockReturnValue({
      data: { exchange_id: ExchangeId.KUCOIN, fiat: "USDT" },
      isLoading: false,
    });
  });

  testCase(
    "calculates HAEDAL beta on a new-bot page from its candles",
    async () => {
      const fetchMock = vi.fn(async (url: string) =>
        response(url.includes("symbol=HAEDALUSDTM") ? 1.5 : 1),
      );

      vi.stubGlobal("fetch", fetchMock);

      const { result } = renderHook(() =>
        useRiskBeta("HAEDALUSDTM", MarketType.FUTURES),
      );

      expectValue(result.current.isLoading).toBe(true);
      await waitFor(() => expectValue(result.current.isLoading).toBe(false));
      expectValue(result.current.beta).toBeCloseTo(1.5, 10);
      expectValue(
        fetchMock.mock.calls.map(([url]) =>
          new URL(url, "http://localhost").searchParams.get("symbol"),
        ),
      ).toEqual(["XBTUSDTM", "HAEDALUSDTM"]);
    },
  );

  testCase(
    "BTC has beta one and shares the benchmark candle request",
    async () => {
      const fetchMock = vi.fn(async () => response(1));

      vi.stubGlobal("fetch", fetchMock);

      const { result } = renderHook(() =>
        useRiskBeta("XBTUSDTM", MarketType.FUTURES),
      );

      await waitFor(() => expectValue(result.current.isLoading).toBe(false));
      expectValue(result.current.beta).toBe(1);
      expectValue(fetchMock).toHaveBeenCalledTimes(1);
    },
  );

  testCase(
    "recalculates when selecting another symbol and ignores stale responses",
    async () => {
      let resolveOldRequest!: (value: ReturnType<typeof response>) => void;

      const oldRequest = new Promise<ReturnType<typeof response>>((resolve) => {
        resolveOldRequest = resolve;
      });

      const fetchMock = vi.fn((url: string, _options: RequestInit) => {
        if (url.includes("symbol=HAEDALUSDTM")) return oldRequest;
        return Promise.resolve(
          response(url.includes("symbol=ETHUSDTM") ? -0.5 : 1),
        );
      });

      vi.stubGlobal("fetch", fetchMock);

      const { result, rerender } = renderHook(
        ({ symbol }) => useRiskBeta(symbol, MarketType.FUTURES),
        { initialProps: { symbol: "HAEDALUSDTM" } },
      );

      const oldSignal = fetchMock.mock.calls[0][1].signal;

      rerender({ symbol: "ETHUSDTM" });

      expectValue(oldSignal?.aborted).toBe(true);
      await waitFor(() => expectValue(result.current.isLoading).toBe(false));
      expectValue(result.current.beta).toBeCloseTo(-0.5, 10);

      await act(async () => resolveOldRequest(response(3)));
      expectValue(result.current.beta).toBeCloseTo(-0.5, 10);
    },
  );

  testCase("uses the selected KuCoin spot pair's quote currency", async () => {
    const fetchMock = vi.fn(async (url: string) => ({
      ok: true,
      json: async () => ({
        data: futuresRows(url.includes("symbol=ETH-USDC") ? 1.5 : 1).map(
          ([timestamp, , , , close]) => [timestamp / 1000, 0, close, 0, 0],
        ),
      }),
    }));

    vi.stubGlobal("fetch", fetchMock);

    const { result } = renderHook(() =>
      useRiskBeta("ETH-USDC", MarketType.SPOT),
    );

    await waitFor(() => expectValue(result.current.isLoading).toBe(false));
    expectValue(result.current.beta).toBeCloseTo(1.5, 10);
    expectValue(fetchMock.mock.calls[0][0]).toContain("symbol=BTC-USDC");
  });

  testCase.each(["failed request", "insufficient history"])(
    "reports unavailable for %s",
    async (reason) => {
      vi.stubGlobal(
        "fetch",
        vi.fn(async () => ({
          ok: reason !== "failed request",
          status: 503,
          json: async () => ({ data: futuresRows(1).slice(-10) }),
        })),
      );

      const { result } = renderHook(() =>
        useRiskBeta("HAEDALUSDTM", MarketType.FUTURES),
      );

      await waitFor(() => expectValue(result.current.isLoading).toBe(false));
      expectValue(result.current.beta).toBeNull();
    },
  );
});
