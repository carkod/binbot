import { notifification } from "../../utils/api";
import { userApiSlice } from "../userApiSlice";
import type { GridLadder } from "./types";

type GridLadderResponse = {
  data: GridLadder;
  message: string;
  error: number;
};

type GridLaddersResponse = {
  data: GridLadder[];
  message: string;
  error: number;
};

type CloseGridLadderParams = {
  id: string;
  reason: string;
};

export const gridLaddersApiSlice = userApiSlice.injectEndpoints({
  endpoints: (build) => ({
    getGridLadders: build.query<GridLadder[], { limit?: number; offset?: number }>({
      query: ({ limit = 100, offset = 0 } = {}) => ({
        url: "/grid-ladders",
        method: "GET",
        params: { limit, offset },
      }),
      providesTags: (result) => [
        "grid-ladders",
        ...(result ?? []).map((ladder) => ({ type: "grid-ladder" as const, id: ladder.id })),
      ],
      transformResponse: ({ data, message, error }: GridLaddersResponse) => {
        if (error === 1) {
          notifification("error", message);
        }
        return data;
      },
    }),
    getActiveGridLadders: build.query<GridLadder[], void>({
      query: () => ({
        url: "/grid-ladders/active",
        method: "GET",
      }),
      providesTags: (result) => [
        "grid-ladders",
        ...(result ?? []).map((ladder) => ({ type: "grid-ladder" as const, id: ladder.id })),
      ],
      transformResponse: ({ data, message, error }: GridLaddersResponse) => {
        if (error === 1) {
          notifification("error", message);
        }
        return data;
      },
    }),
    getGridLadder: build.query<GridLadder, string>({
      query: (id) => ({
        url: `/grid-ladders/${id}`,
        method: "GET",
      }),
      providesTags: (result, error, id) => [{ type: "grid-ladder", id: result?.id ?? id }],
      transformResponse: ({ data, message, error }: GridLadderResponse) => {
        if (error === 1) {
          notifification("error", message);
        }
        return data;
      },
    }),
    closeGridLadder: build.mutation<GridLadder, CloseGridLadderParams>({
      query: ({ id, reason }) => ({
        url: `/grid-ladders/${id}/close`,
        method: "POST",
        body: { reason },
      }),
      invalidatesTags: (result, error, arg) => ["grid-ladders", { type: "grid-ladder", id: arg.id }],
      transformResponse: ({ data, message, error }: GridLadderResponse) => {
        if (error === 1) {
          notifification("error", message);
        } else {
          notifification("success", message);
        }
        return data;
      },
    }),
  }),
});

export const {
  useGetGridLaddersQuery,
  useGetActiveGridLaddersQuery,
  useGetGridLadderQuery,
  useCloseGridLadderMutation,
} = gridLaddersApiSlice;
