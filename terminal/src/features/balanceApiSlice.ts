import type { StandardResponse } from "../utils/api.types";
import { notifification, readApiResponse } from "../utils/api";
import type { BalanceData, BenchmarkCollection } from "./features.types";
import { userApiSlice } from "./userApiSlice";

export const balancesApiSlice = userApiSlice.injectEndpoints({
  endpoints: (build) => ({
    getBalance: build.query<BalanceData, void>({
      query: () => ({
        url: `${import.meta.env.VITE_ACCOUNT_BALANCE}` || "/balance",
        providesTags: ["balances"],
      }),
      transformResponse: (response: StandardResponse) =>
        readApiResponse(response),
    }),
    getBenchmark: build.query<BenchmarkCollection, void>({
      query: () => ({
        url: `${import.meta.env.VITE_BALANCE_SERIES}` || "/balance",
        providesTags: ["benchmark"],
      }),
      transformResponse: ({ data, message, error }) => {
        if (error && error === 1) {
          notifification("error", message);
        }

        const { series, stats } = data;

        // Convert to % so graph is normalized
        series.dates.shift();
        let percentageSeries = {
          datesSeries: series.dates,
          btcSeries: [],
          fiatSeries: [],
        };
        series.btc.forEach((element: number, index: number) => {
          if (index > 0) {
            const previousQty = series.btc[index - 1];

            const diff = (element - previousQty) / element;

            percentageSeries.btcSeries.push(diff * 100);
          }
        });
        series.fiat.forEach((element: number, index: number) => {
          if (index > 0) {
            const previousQty = series.fiat[index - 1];

            const diff = (element - previousQty) / element;

            percentageSeries.fiatSeries.push(diff * 100);
          }
        });

        return {
          benchmarkData: data.series,
          percentageSeries: percentageSeries,
          portfolioStats: {
            pnl: stats.pnl,
            sharpe: stats.sharpe,
            btc_sharpe: stats.btc_sharpe,
          },
        };
      },
    }),
  }),
});

export const { useGetBalanceQuery, useGetBenchmarkQuery } = balancesApiSlice;
