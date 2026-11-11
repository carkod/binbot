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
  adr_ratio: number[];
  adr_ma: number[];
}

export interface GainersLosersAggregatePoint {
  timestamp: string;
  gainer_magnitude: number;
  loser_magnitude: number;
  advancers: number;
  decliners: number;
}

export interface FastestMover {
  symbol: string;
  price_change_1h_percent: number;
  price_change_3h_percent: number | null;
  price_change_percent: number;
  last_price: number;
  turnover_24h: number;
}

export interface FastestMoversSnapshot {
  source: string;
  recorded_at: string | null;
  comparison_at: string | null;
  gainers: FastestMover[];
  losers: FastestMover[];
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
    fastestMovers: build.query<FastestMoversSnapshot, void>({
      query: () => ({ url: "/charts/fastest_movers?limit=10" }),
      transformResponse: ({ data, message, error }) => {
        if (error === 1) {
          notifification("error", message);
        }
        return data;
      },
    }),
    gainersLosersAggregate: build.query<GainersLosersAggregatePoint[], void>({
      query: () => ({
        url: "/charts/gainers-losers-aggregate?limit=672",
      }),
      transformResponse: ({ data, message, error }) => {
        if (error && error === 1) {
          notifification("error", message);
        }

        return data;
      },
    }),
  }),
});

export const { useFastestMoversQuery, useGainersLosersAggregateQuery } =
  marketApiSlice;
