import { createApi, fetchBaseQuery } from "@reduxjs/toolkit/query/react";
import { notifification } from "../utils/api";
import { floatSafe } from "../utils/math";

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
      new Date(timestamp).toISOString(),
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
  useBtcCloseSeriesQuery,
  useFuturesRankingsQuery,
  useFuturesContractQuery,
} = kucoinApiSlice;
