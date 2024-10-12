import { notifification } from "../utils/api"
import { userApiSlice } from "./userApiSlice"

interface AssetCollection {
  asset: string
  free: number
  locked: number
}

export interface BalanceEstimateData {
  total_fiat: number
  balances: AssetCollection[]
  fiat_left: number
  estimated_total_btc: number
  estimated_total_fiat: number
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
  }),
})

export const { useGetRawBalanceQuery, useGetEstimateQuery } = balancesApiSlice
