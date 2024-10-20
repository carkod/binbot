import { notifification } from "../utils/api"
import { userApiSlice } from "./userApiSlice"

interface AssetCollection {
  asset: string
  free: number
  locked: number
}

export interface BalanceEstimateData {
  asset: string
  total_fiat: number
  balances: AssetCollection[]
  fiat_left: number
  estimated_total_btc: number
  estimated_total_fiat: number
}

// Benchmark of portfolio (in USDC at time of writing) against BTC
export interface BenchmarkData {
  usdc: number[]
  btc: number[]
  dates: string[]
}

export interface BenchmarkSeriesData {
  usdcSeries: number[]
  btcSeries: number[]
  datesSeries: string[]
}


export interface BenchmarkCollection {
  benchmarkData: BenchmarkData
  percentageSeries: BenchmarkSeriesData
}

export const balancesApiSlice = userApiSlice.injectEndpoints({
  endpoints: build => ({
    getRawBalance: build.query<AssetCollection[], void>({
      query: () => ({
        url: `${import.meta.env.VITE_ACCOUNT_BALANCE_RAW}` || "/balance",
        providesTags: ["balances"],
      }),
      transformResponse: ({ data, message, error }, meta, arg) => {
        if (error && error === 1) {
          notifification("error", message)
        } else {
          notifification("success", message)
        }

        return data
      },
    }),
    getEstimate: build.query<BalanceEstimateData, void>({
      query: () => ({
        url: `${import.meta.env.VITE_BALANCE_ESTIMATE}` || "/balance",
        providesTags: ["balances"],
      }),
      transformResponse: ({ data, message, error }, meta, arg) => {
        if (error && error === 1) {
          notifification("error", message)
        } else {
          notifification("success", message)
        }

        return data
      },
    }),
    getBenchmark: build.query<BenchmarkCollection, void>({
      query: () => ({
        url: `${import.meta.env.VITE_BALANCE_SERIES}` || "/balance",
        providesTags: ["benchmark"],
      }),
      transformResponse: ({ data, message, error }, meta, arg) => {
        if (error && error === 1) {
          notifification("error", message)
        } else {
          notifification("success", message)
        }
        // Convert to % so graph is normalized
        data.dates.shift()
        let percentageSeries = {
          datesSeries: data.dates,
          btcSeries: [],
          usdcSeries: [],
        }
        data.btc.forEach((element, index) => {
          if (index > 0) {
            const previousQty = data.btc[index - 1];
            const diff = (previousQty - element) / previousQty
            percentageSeries.btcSeries.push(diff * 100);
          }
        });
        data.usdc.forEach((element, index) => {
          if (index > 0) {
            const previousQty = data.usdc[index - 1];
            const diff = (previousQty - element) / previousQty
            percentageSeries.usdcSeries.push(diff * 100);
          }
        });

        return {
          benchmarkData: data,
          percentageSeries: percentageSeries,
        }
      },
    }),
  }),
})

export const {
  useGetRawBalanceQuery,
  useGetEstimateQuery,
  useGetBenchmarkQuery,
} = balancesApiSlice
