import { useEffect, useState } from "react";
import { useGetSettingsQuery } from "../../features/autotradeApiSlice";
import { useGetBotsQuery } from "../../features/bots/botsApiSlice";
import { type BalanceData } from "../../features/features.types";
import { buildBackUrl } from "../../utils/api";
import { BotStatus, ExchangeId, MarketType } from "../../utils/enums";
import { getToken } from "../../utils/login";
import {
  calculateRiskBeta,
  FIFTEEN_MINUTES_MS,
  RISK_BETA_CANDLE_COUNT,
  type CandleClose,
  type RiskExposure,
} from "../../utils/riskBeta";

async function fetchJson(url: string, signal: AbortSignal, token?: string) {
  const response = await fetch(url, {
    signal,
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
  });
  if (!response.ok)
    throw new Error(`Risk beta data request failed: ${response.status}`);
  return response.json();
}

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

  const response = await fetchJson(url, signal);
  const rows =
    exchange === ExchangeId.BINANCE && !futures ? response : response.data;
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

export function useRiskBeta(accountData: BalanceData, marketType: MarketType) {
  const { data: settings, isLoading: loadingSettings } = useGetSettingsQuery();
  const { data: activeBots, isLoading: loadingBots } = useGetBotsQuery(
    { status: BotStatus.ACTIVE },
    { skip: marketType !== MarketType.FUTURES },
  );
  const [beta, setBeta] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (loadingSettings || (marketType === MarketType.FUTURES && loadingBots)) {
      setIsLoading(true);
      return;
    }
    if (!settings || (marketType === MarketType.FUTURES && !activeBots)) {
      setBeta(null);
      setIsLoading(false);
      return;
    }

    const controller = new AbortController();
    const completedBefore =
      Math.floor(Date.now() / FIFTEEN_MINUTES_MS) * FIFTEEN_MINUTES_MS;
    const exchange = settings.exchange_id;
    const fiat = accountData.fiat_currency;
    setBeta(null);
    setIsLoading(true);

    async function calculate() {
      if (
        marketType === MarketType.FUTURES &&
        (exchange !== ExchangeId.KUCOIN || fiat !== "USDT")
      ) {
        return null;
      }

      const benchmarkSymbol =
        marketType === MarketType.FUTURES
          ? "XBTUSDTM"
          : exchange === ExchangeId.KUCOIN
            ? `BTC-${fiat}`
            : `BTC${fiat}`;
      const benchmark = await loadCandles(
        benchmarkSymbol,
        exchange,
        completedBefore,
        controller.signal,
        marketType === MarketType.FUTURES,
      );
      let exposures: RiskExposure[];

      if (marketType === MarketType.FUTURES) {
        const pairs = [
          ...new Set(
            activeBots!.bots.ids
              .map((id) => activeBots!.bots.entities[id])
              .filter((bot) => bot?.market_type === MarketType.FUTURES)
              .map((bot) => bot!.pair),
          ),
        ];
        exposures = (
          await Promise.all(
            pairs.map(async (pair) => {
              const positionResponse = await fetchJson(
                `${buildBackUrl()}/order/kucoin/futures/position/${encodeURIComponent(pair)}`,
                controller.signal,
                getToken(),
              );
              if (positionResponse.error)
                throw new Error("Position request failed");
              const position = positionResponse.data;
              if (!position?.is_open || !position.current_qty) return null;
              if (position.is_inverse || position.settle_currency !== fiat) {
                throw new Error("Unsupported futures position");
              }
              const [contractResponse, candles] = await Promise.all([
                fetchJson(
                  `/kucoin-futures/api/v1/contracts/${encodeURIComponent(pair)}`,
                  controller.signal,
                ),
                pair === benchmarkSymbol
                  ? Promise.resolve(benchmark)
                  : loadCandles(
                      pair,
                      exchange,
                      completedBefore,
                      controller.signal,
                      true,
                    ),
              ]);
              const multiplier = Number(contractResponse.data?.multiplier);
              if (!Number.isFinite(multiplier) || multiplier <= 0) {
                throw new Error("Invalid futures contract multiplier");
              }
              return {
                quantity: Number(position.current_qty) * multiplier,
                candles,
              };
            }),
          )
        ).filter((exposure): exposure is RiskExposure => exposure !== null);
      } else {
        exposures = await Promise.all(
          Object.entries(accountData.balances)
            .filter(([asset, quantity]) => asset !== fiat && quantity > 0)
            .map(async ([asset, quantity]) => ({
              quantity,
              candles:
                asset === "BTC"
                  ? benchmark
                  : await loadCandles(
                      exchange === ExchangeId.KUCOIN
                        ? `${asset}-${fiat}`
                        : `${asset}${fiat}`,
                      exchange,
                      completedBefore,
                      controller.signal,
                    ),
            })),
        );
      }

      return calculateRiskBeta(
        benchmark,
        exposures,
        accountData.estimated_total_fiat,
        completedBefore,
      );
    }

    calculate()
      .then((value) => {
        if (!controller.signal.aborted) setBeta(value);
      })
      .catch(() => {
        if (!controller.signal.aborted) setBeta(null);
      })
      .finally(() => {
        if (!controller.signal.aborted) setIsLoading(false);
      });

    return () => controller.abort();
  }, [
    accountData,
    activeBots,
    loadingBots,
    loadingSettings,
    marketType,
    settings,
  ]);

  return { beta, isLoading };
}
