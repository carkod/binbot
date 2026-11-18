import { createApi, fetchBaseQuery } from "@reduxjs/toolkit/query/react";
import { getApiErrorMessage, notifification } from "../utils/api";
import { floatSafe } from "../utils/math";
import {
  analyzeKucoinOrderBook,
  type KucoinOrderBook,
  type ObiSnapshot,
} from "./kucoinLiquidity";

export interface KucoinFuturesTicker24 {
  sequence: number;
  symbol: string;
  side: "buy" | "sell";
  size: number;
  tradeId: string;
  price: string;
  bestBidPrice: string;
  bestBidSize: number;
  bestAskPrice: string;
  bestAskSize: number;
  ts: number;
}

export interface KucoinFuturesContract {
  symbol: string;
  multiplier: number;
}

type KucoinFuturesKline = [
  timestamp: number,
  open: number | string,
  high: number | string,
  low: number | string,
  close: number | string,
  volume: number | string,
  turnover: number | string,
];

type KucoinFuturesKlineResponse = {
  code: string;
  data: KucoinFuturesKline[];
};

export interface BtcCloseSeries {
  symbol: "XBTUSDTM";
  interval: "15m";
  timestamp: string[];
  close: number[];
}

const FIFTEEN_MINUTES_MS = 15 * 60 * 1000;

export const transformBtcCloseSeries = ({
  data,
}: KucoinFuturesKlineResponse): BtcCloseSeries => {
  const chronologicalCandles = [...data].sort(
    (left, right) => left[0] - right[0],
  );

  return {
    symbol: "XBTUSDTM",
    interval: "15m",
    timestamp: chronologicalCandles.map(([timestamp]) =>
      new Date(timestamp + FIFTEEN_MINUTES_MS).toISOString(),
    ),
    close: chronologicalCandles.map((candle) => Number(candle[4])),
  };
};

/**
 * Kucoin Futures API slice
 *
 * Calling Kucoin Futures API directly to reduce weight of requests to Binbot API
 * backend already makes a lot of requests
 */
export const kucoinApiSlice = createApi({
  baseQuery: fetchBaseQuery({
    baseUrl: "/kucoin-futures/api/v1",
  }),
  reducerPath: "kucoinApi",
  endpoints: (build) => ({
    futuresLiquidity: build.query<ObiSnapshot, string>({
      async queryFn(symbol, _api, _extraOptions, baseQuery) {
        const [bookResult, contractResult] = await Promise.all([
          baseQuery({ url: "/level2/depth100", params: { symbol } }),
          baseQuery({ url: `/contracts/${encodeURIComponent(symbol)}` }),
        ]);

        if (bookResult.error) return { error: bookResult.error };
        if (contractResult.error) return { error: contractResult.error };

        const book = bookResult.data as {
          code: string;
          data?: KucoinOrderBook;
        };

        const contract = contractResult.data as {
          code: string;
          data?: {
            symbol: string;
            multiplier: number | string;
            quoteCurrency: string;
            isInverse: boolean;
          };
        };

        try {
          if (book?.code !== "200000") {
            throw new Error(
              getApiErrorMessage(
                { data: book },
                "KuCoin order-book request failed",
              ),
            );
          }
          if (contract?.code !== "200000") {
            throw new Error(
              getApiErrorMessage(
                { data: contract },
                "KuCoin contract request failed",
              ),
            );
          }
          if (
            book.data?.symbol !== symbol ||
            contract.data?.symbol !== symbol ||
            contract.data.quoteCurrency !== "USDT" ||
            contract.data.isInverse !== false
          ) {
            throw new Error("KuCoin USDT futures liquidity is unavailable");
          }

          // KuCoin Futures depth timestamps are Unix nanoseconds.
          const timestamp = Number(book.data.ts) / 1_000_000;

          if (!Number.isFinite(timestamp) || timestamp <= 0) {
            throw new Error("Invalid KuCoin snapshot timestamp");
          }
          return {
            data: {
              ...analyzeKucoinOrderBook(
                book.data,
                Number(contract.data.multiplier),
              ),
              timestamp,
              multiplier: Number(contract.data.multiplier),
            },
          };
        } catch (error) {
          return {
            error: {
              status: "CUSTOM_ERROR",
              error:
                error instanceof Error
                  ? error.message
                  : "Invalid KuCoin liquidity data",
            },
          };
        }
      },
    }),
    btcCloseSeries: build.query<BtcCloseSeries, void>({
      query: () => ({
        url: import.meta.env.VITE_KUCOIN_BTC_KLINES || "/kline/query",
        params: {
          symbol: "XBTUSDTM",
          granularity: 15,
        },
      }),
      transformResponse: transformBtcCloseSeries,
    }),
    futuresRankings: build.query<any, void>({
      query: () => ({
        url: `${import.meta.env.VITE_KUCOIN_TICKER_24}`,
        providesTags: ["kucoin"],
      }),
      transformResponse: (data: any, meta) => {
        if (!meta.response.ok) {
          notifification("error", meta.response.statusText);
        }

        const allPercentageChanges = data.data
          .map((ticker: any) => ({
            symbol: ticker.symbol,
            priceChangePercent: String(
              floatSafe(ticker.priceChgPct ?? ticker.changeRate) * 100,
            ),
          }))
          .sort(
            (a: any, b: any) =>
              parseFloat(a.priceChangePercent) -
              parseFloat(b.priceChangePercent),
          )
          .reverse();

        return allPercentageChanges;
      },
    }),
    futuresContract: build.query<KucoinFuturesContract, string>({
      query: (symbol) => ({
        url: `/contracts/${symbol}`,
      }),
      transformResponse: (data: any) => ({
        symbol: data.data.symbol,
        multiplier: floatSafe(data.data.multiplier) || 1,
      }),
    }),
  }),
});

export const {
  useFuturesLiquidityQuery,
  useBtcCloseSeriesQuery,
  useFuturesRankingsQuery,
  useFuturesContractQuery,
} = kucoinApiSlice;
