import { notifification } from "../utils/api";
import type {
  BalanceData,
  BenchmarkCollection,
} from "./features.types";
import { userApiSlice } from "./userApiSlice";

export const balancesApiSlice = userApiSlice.injectEndpoints({
  endpoints: (build) => ({
    getBalance: build.query<BalanceData, void>({
      query: () => ({
        url: `${import.meta.env.VITE_ACCOUNT_BALANCE}` || "/balance",
        providesTags: ["balances"],
      }),
      transformResponse: ({ data, message, error }, meta, arg) => {
        if (error && error === 1) {
          notifification("error", message);
        }

        return data;
      },
    }),
    getBenchmark: build.query<BenchmarkCollection, void>({
      query: () => ({
        url: `${import.meta.env.VITE_BALANCE_SERIES}` || "/balance",
        providesTags: ["benchmark"],
      }),
      transformResponse: ({ data, message, error }, meta) => {
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
          portfolioStats: stats,
        };
      },
    }),
  }),
});

export const { useGetBalanceQuery, useGetBenchmarkQuery } = balancesApiSlice;
