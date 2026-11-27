import { useEffect, useState } from "react";
import { useGetSettingsQuery } from "../../features/autotradeApiSlice";
import { ExchangeId, MarketType } from "../../utils/enums";
import { floorToMultiple } from "../../utils/math";
import {
  calculateRiskBeta,
  FIFTEEN_MINUTES_MS,
  RISK_BETA_CANDLE_COUNT,
  type CandleClose,
} from "../../utils/riskBeta";

export async function loadCandles(
  symbol: string,
  exchange: ExchangeId,
  completedBefore: number,
  signal: AbortSignal,
  futures = false,
): Promise<CandleClose[]> {
  const start =
    completedBefore - (RISK_BETA_CANDLE_COUNT + 2) * FIFTEEN_MINUTES_MS;

  let url: string;
  if (futures) {
    const params = new URLSearchParams({
      symbol,
      granularity: "15",
      from: String(start),
      to: String(completedBefore - 1),
    });

    url = `/kucoin-futures/api/v1/kline/query?${params}`;
  } else if (exchange === ExchangeId.KUCOIN) {
    const params = new URLSearchParams({
      symbol,
      type: "15min",
      startAt: String(Math.floor(start / 1000)),
      endAt: String(Math.floor((completedBefore - 1) / 1000)),
    });

    url = `/kucoin/api/v1/market/candles?${params}`;
  } else {
    const params = new URLSearchParams({
      symbol,
      interval: "15m",
      limit: String(RISK_BETA_CANDLE_COUNT),
      endTime: String(completedBefore - 1),
    });

    url = `/binance/api/v3/klines?${params}`;
  }

  const response = await fetch(url, { signal });

  if (!response.ok)
    throw new Error(`Risk beta data request failed: ${response.status}`);

  const payload = await response.json();

  const rows =
    exchange === ExchangeId.BINANCE && !futures ? payload : payload.data;

  if (!Array.isArray(rows)) throw new Error("Invalid candlestick response");
  return rows.map((row: unknown) => {
    if (!Array.isArray(row)) throw new Error("Invalid candlestick row");
    return {
      timestamp:
        Number(row[0]) *
        (exchange === ExchangeId.KUCOIN && !futures ? 1000 : 1),
      close: Number(row[exchange === ExchangeId.KUCOIN && !futures ? 2 : 4]),
    };
  });
}

export function useRiskBeta(symbol: string, marketType: MarketType) {
  const { data: settings, isLoading: loadingSettings } = useGetSettingsQuery();

  const exchange = settings?.exchange_id;

  const fiat = settings?.fiat;

  const [beta, setBeta] = useState<number | null>(null);

  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    setBeta(null);
    if (loadingSettings) {
      setIsLoading(true);
      return;
    }
    if (
      !symbol ||
      !exchange ||
      !fiat ||
      (marketType === MarketType.FUTURES &&
        (exchange !== ExchangeId.KUCOIN || !symbol.endsWith("USDTM")))
    ) {
      setIsLoading(false);
      return;
    }

    const controller = new AbortController();

    const completedBefore = floorToMultiple(Date.now(), FIFTEEN_MINUTES_MS);

    const futures = marketType === MarketType.FUTURES;

    const benchmarkSymbol = futures
      ? "XBTUSDTM"
      : exchange === ExchangeId.KUCOIN
        ? `BTC-${symbol.split("-")[1] ?? fiat}`
        : `BTC${fiat}`;

    setIsLoading(true);

    const benchmarkRequest = loadCandles(
      benchmarkSymbol,
      exchange,
      completedBefore,
      controller.signal,
      futures,
    );

    Promise.all([
      benchmarkRequest,
      symbol === benchmarkSymbol
        ? benchmarkRequest
        : loadCandles(
            symbol,
            exchange,
            completedBefore,
            controller.signal,
            futures,
          ),
    ])
      .then(([benchmark, asset]) => {
        if (!controller.signal.aborted)
          setBeta(calculateRiskBeta(benchmark, asset, completedBefore));
      })
      .catch(() => {
        if (!controller.signal.aborted) setBeta(null);
      })
      .finally(() => {
        if (!controller.signal.aborted) setIsLoading(false);
      });

    return () => controller.abort();
  }, [symbol, marketType, exchange, fiat, loadingSettings]);

  return { beta, isLoading };
}
