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
  }),
});

export const { useFuturesRankingsQuery } = kucoinApiSlice;
