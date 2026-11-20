import type { StandardResponse } from "../utils/api.types";
import { readApiResponse } from "../utils/api";
import { userApiSlice } from "./userApiSlice";

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
    cvdSymbol: build.query<CvdSymbol, string>({
      query: (symbol) => ({
        url: "/charts/cvd-symbol",
        params: { symbol, limit: 15 },
      }),
    }),
    cvdAggregate: build.query<CvdAggregate, void>({
      query: () => ({ url: "/charts/cvd-aggregate?limit=672" }),
    }),
    fastestMovers: build.query<FastestMoversSnapshot, void>({
      query: () => ({ url: "/charts/fastest_movers?limit=10" }),
      transformResponse: (response: StandardResponse) =>
        readApiResponse(response),
    }),
    gainersLosersAggregate: build.query<GainersLosersAggregatePoint[], void>({
      query: () => ({
        url: "/charts/gainers-losers-aggregate?limit=672",
      }),
      transformResponse: (response: StandardResponse) =>
        readApiResponse(response),
    }),
  }),
});

export const {
  useFastestMoversQuery,
  useGainersLosersAggregateQuery,
  useCvdAggregateQuery,
  useCvdSymbolQuery,
} = marketApiSlice;

export interface CvdPoint {
  timestamp: string;
  buy: number | null;
  sell: number | null;
  cvd: number | null;
  expected_symbols: number | null;
  covered_symbols: number;
  observed_minutes: number;
  complete: boolean;
  gap: boolean;
  current: boolean;
  universe_changed: boolean;
}

export interface CvdAggregate {
  source: string;
  data: CvdPoint[];
  reset_at: string;
  updated_at: string | null;
  stale: boolean;
  partial: boolean;
}

export interface CvdSymbol extends CvdAggregate {
  symbol: string;
}
