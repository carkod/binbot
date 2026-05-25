import { notifification } from "../../utils/api";
import { userApiSlice } from "../userApiSlice";
import type { GridLadder } from "./types";

type GridLadderResponse = {
  detail: GridLadder;
};

type GridLaddersResponse = {
  detail: GridLadder[];
};

type CloseGridLadderParams = {
  id: string;
  reason: string;
};

export const gridLaddersApiSlice = userApiSlice.injectEndpoints({
  endpoints: (build) => ({
    getGridLadders: build.query<
      GridLadder[],
      { limit?: number; offset?: number }
    >({
      query: ({ limit = 100, offset = 0 } = {}) => ({
        url: "/grid-ladders",
        method: "GET",
        params: { limit, offset },
      }),
      providesTags: (result) => [
        "grid-ladders",
        ...(result ?? []).map((ladder) => ({
          type: "grid-ladder" as const,
          id: ladder.id,
        })),
      ],
      transformResponse: ({ detail }: GridLaddersResponse) => detail,
    }),
    getActiveGridLadders: build.query<GridLadder[], void>({
      query: () => ({
        url: "/grid-ladders/active",
        method: "GET",
      }),
      providesTags: (result) => [
        "grid-ladders",
        ...(result ?? []).map((ladder) => ({
          type: "grid-ladder" as const,
          id: ladder.id,
        })),
      ],
      transformResponse: ({ detail }: GridLaddersResponse) => detail,
    }),
    getGridLadder: build.query<GridLadder, string>({
      query: (id) => ({
        url: `/grid-ladders/${id}`,
        method: "GET",
      }),
      providesTags: (result, error, id) => [
        { type: "grid-ladder", id: result?.id ?? id },
      ],
      transformResponse: ({ detail }: GridLadderResponse) => detail,
    }),
    deleteGridLadder: build.mutation<void, string>({
      query: (id) => ({
        url: `/grid-ladders/${id}`,
        method: "DELETE",
      }),
      invalidatesTags: (result, error, id) => [
        "grid-ladders",
        { type: "grid-ladder", id },
      ],
    }),
    closeGridLadder: build.mutation<GridLadder, CloseGridLadderParams>({
      query: ({ id, reason }) => ({
        url: `/grid-ladders/${id}/close`,
        method: "POST",
        body: { reason },
      }),
      invalidatesTags: (result, error, arg) => [
        "grid-ladders",
        { type: "grid-ladder", id: arg.id },
      ],
      transformResponse: ({ detail }: GridLadderResponse) => {
        notifification("success", "Grid ladder closed");
        return detail;
      },
    }),
  }),
});

export const {
  useGetGridLaddersQuery,
  useGetActiveGridLaddersQuery,
  useGetGridLadderQuery,
  useDeleteGridLadderMutation,
  useCloseGridLadderMutation,
} = gridLaddersApiSlice;
