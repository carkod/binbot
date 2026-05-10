import { notifification } from "../utils/api";
import { weekAgo } from "../utils/time";
import { userApiSlice } from "./userApiSlice";

export type SignalRecord = {
  id: number;
  algorithm_name: string;
  symbol: string;
  generated_at: string;
  direction: string;
  autotrade: boolean;
  current_regime?: string | null;
  context?: Record<string, unknown> | null;
  bot_params?: Record<string, unknown> | null;
  indicators?: Record<string, unknown> | null;
};

export type GetSignalsParams = {
  limit?: number;
  offset?: number;
  since?: string | number | Date;
  until?: string | number | Date;
  include_payload?: boolean;
};

type SignalsListResponse = {
  data: SignalRecord[];
  message: string;
  error: number;
};

const formatDateQueryParam = (value: string | number | Date) => {
  if (value instanceof Date) return value.toISOString();
  if (typeof value === "number") return new Date(value).toISOString();
  return value;
};

export const signalsApiSlice = userApiSlice.injectEndpoints({
  endpoints: (build) => ({
    getSignals: build.query<SignalRecord[], GetSignalsParams | void>({
      query: (queryParams) => {
        const params = (queryParams ?? {}) as GetSignalsParams;
        const {
          limit = 1000,
          offset = 0,
          since = weekAgo(),
          until = new Date(),
          include_payload = false,
        } = params;

        return {
          url: import.meta.env.VITE_SIGNALS || "/signals",
          method: "GET",
          params: {
            limit,
            offset,
            since: formatDateQueryParam(since),
            until: formatDateQueryParam(until),
            include_payload,
          },
        };
      },
      transformResponse: ({ data, message, error }: SignalsListResponse) => {
        if (error && error === 1) {
          notifification("error", message);
        }

        return data;
      },
      transformErrorResponse: (error: {
        status: number | string;
        data?: unknown;
      }) => {
        if (typeof error.status === "number" && error.status >= 400) {
          const detail =
            typeof error.data === "object" &&
            error.data !== null &&
            "detail" in error.data &&
            typeof error.data.detail === "string"
              ? error.data.detail
              : "Unable to load signals";

          notifification("error", detail);
        }

        return error;
      },
    }),
  }),
});

export const { useGetSignalsQuery } = signalsApiSlice;
