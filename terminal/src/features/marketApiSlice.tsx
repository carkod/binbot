import { notifification } from "../utils/api";
import { userApiSlice } from "./userApiSlice";

export interface GainerLosersData {
  dates: string[];
  gainers_percent: number[];
  losers_percent: number[];
  gainers_count: number[];
  losers_count: number[];
  total_volume: number[];
  gainers: string[];
  losers: string[];
}

function computerPercent(data) {
  const gainers = [];
  const losers = [];

  for (let i = 0; i < data.gainers_percent.length; i++) {
    const totalCount = data.gainers_count[i] + data.losers_count[i];
    const gainersCount =
      ((data.gainers_count[i] / totalCount) * 100).toFixed(2) + "%";
    const losersCount =
      ((data.losers_count[i] / totalCount) * 100).toFixed(2) + "%";
    gainers.push(gainersCount);
    losers.push(losersCount);
  }
  return { gainers, losers };
}

/**
 * Difference between balanceApiSlice and marketApiSlice
 * is one comes from market the other comes from binance account.
 * Everything that comes from market, doesn't require authentication/Signed URLs.
 *
 * Some other data such as benchmark, are a mix of both market and account data, those should be in the balanceApiSlice, because at least one requires authentication.
 */
export const marketApiSlice = userApiSlice.injectEndpoints({
  endpoints: (build) => ({
    gainerLosersSeries: build.query<GainerLosersData, void>({
      query: () => ({
        url:
          `${import.meta.env.VITE_GAINERS_LOSERS_SERIES}` || "/gainers-losers",
        providesTags: ["balances"],
      }),
      transformResponse: ({ data, message, error }, meta, arg) => {
        if (error && error === 1) {
          notifification("error", message);
        }

        const historicalGLdata = {
          ...data,
          ...computerPercent(data),
        };
        return historicalGLdata;
      },
    }),
  }),
});

export const { useGainerLosersSeriesQuery } = marketApiSlice;
