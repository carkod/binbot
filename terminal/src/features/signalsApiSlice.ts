import { notifification } from "../utils/api";
import { userApiSlice } from "./userApiSlice";

export type SignalRecord = {
  id: number;
  algorithm_name: string;
  symbol: string;
  generated_at: string;
  direction: string;
  autotrade: boolean;
  current_regime?: string | null;
  context: Record<string, unknown>;
  bot_params: Record<string, unknown>;
  indicators: Record<string, unknown>;
};

type GetSignalsParams = {
  limit?: number;
  offset?: number;
};

type SignalsListResponse = {
  data: SignalRecord[];
  message: string;
  error: number;
};

export const signalsApiSlice = userApiSlice.injectEndpoints({
  endpoints: (build) => ({
    getSignals: build.query<SignalRecord[], GetSignalsParams | void>({
      query: ({ limit = 1000, offset = 0 } = {}) => ({
        url: import.meta.env.VITE_SIGNALS || "/signals",
        method: "GET",
        params: {
          limit,
          offset,
        },
      }),
      transformResponse: ({ data, message, error }: SignalsListResponse) => {
        if (error && error === 1) {
          notifification("error", message);
        }

        return data;
      },
      transformErrorResponse: (error: {
        status: number;
        data?: { detail?: string };
      }) => {
        if (error.status >= 400) {
          notifification(
            "error",
            error.data?.detail || "Unable to load signals",
          );
        }

        return error;
      },
    }),
  }),
});

export const { useGetSignalsQuery } = signalsApiSlice;
