import { createApi } from "@reduxjs/toolkit/query/react";
import { binanceBaseQuery, notifification } from "../utils/api";

export interface BinanceTicker24 {
  symbol: string;
  priceChange: string;
  priceChangePercent: string;
  weightedAvgPrice: string;
  prevClosePrice: string;
  lastPrice: string;
  lastQty: string;
  bidPrice: string;
  askPrice: string;
  openPrice: string;
  highPrice: string;
  lowPrice: string;
  volume: string;
  quoteVolume: string;
  openTime: number;
  closeTime: number;
  firstId: number;
  lastId: number;
  count: number;
}

/**
 * Binance API slice
 *
 * The reason of having directly call Binance API
 * instead of using Binbot API proxy
 * is to reduce weight of requests to Binbot API
 */
export const binanceApiSlice = createApi({
  baseQuery: binanceBaseQuery,
  reducerPath: "binanceApi",
  endpoints: (build) => ({
    gainerLosers: build.query<BinanceTicker24[], void>({
      query: () => ({
        url: `${import.meta.env.VITE_TICKER_24}` || "/gainers-losers",
        providesTags: ["binance"],
      }),
      transformResponse: (data: BinanceTicker24[], meta) => {
        if (!meta.response.ok) {
          notifification("error", meta.response.statusText);
        }

        const filterUSDCmarket = data.filter((item) =>
          item.symbol.endsWith("USDC"),
        );
        const usdcData = filterUSDCmarket
          .sort(
            (a, b) =>
              parseFloat(a.priceChangePercent) -
              parseFloat(b.priceChangePercent),
          )
          .reverse();

        return usdcData;
      },
    }),
  }),
});

export const { useGainerLosersQuery } = binanceApiSlice;
