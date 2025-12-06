import { notifification } from "../utils/api";
import type { BalanceData, BenchmarkCollection } from "./features.types";
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
      transformResponse: ({ data, message, error }, meta, arg) => {
        if (error && error === 1) {
          notifification("error", message);
        }

        // Convert to % so graph is normalized
        data.dates.shift();
        let percentageSeries = {
          datesSeries: data.dates,
          btcSeries: [],
          usdcSeries: [],
        };
        data.btc.forEach((element, index) => {
          if (index > 0) {
            const previousQty = data.btc[index - 1];
            const diff = (element - previousQty) / element;
            percentageSeries.btcSeries.push(diff * 100);
          }
        });
        data.usdc.forEach((element, index) => {
          if (index > 0) {
            const previousQty = data.usdc[index - 1];
            const diff = (element - previousQty) / element;
            percentageSeries.usdcSeries.push(diff * 100);
          }
        });

        return {
          benchmarkData: data,
          percentageSeries: percentageSeries,
        };
      },
    }),
  }),
});

export const { useGetBalanceQuery, useGetBenchmarkQuery } = balancesApiSlice;
