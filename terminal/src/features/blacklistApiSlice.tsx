import { notifification } from "../utils/api";
import { userApiSlice } from "./userApiSlice";

export interface BlacklistItem {
  pair: string;
  reason: string;
}

export const blacklistApiSlice = userApiSlice.injectEndpoints({
  endpoints: (build) => ({
    getBlacklist: build.query<BlacklistItem[], void>({
      query: () => ({
        url: `${import.meta.env.VITE_RESEARCH_BLACKLIST}` || "/blacklist",
        providesTags: ["blacklist"],
      }),
      transformResponse: ({ data, message, error }, meta, arg) => {
        if (error && error === 1) {
          notifification("error", message);
        } else {
          notifification("success", message);
        }

        return data;
      },
    }),
    addBlacklistItem: build.mutation<void, BlacklistItem>({
      query: (body) => ({
        url: `${import.meta.env.VITE_RESEARCH_BLACKLIST}` || "/blacklist",
        method: "POST",
        body,
        invalidatesTags: ["blacklist"],
      }),
      transformResponse: ({ data, message, error }, meta, arg) => {
        if (error && error === 1) {
          notifification("error", message);
        } else {
          notifification("success", message);
        }
        return data;
      },
    }),
    deleteBlacklistItem: build.mutation<void, string>({
      query: ({ pair }) => ({
        url:
          `${import.meta.env.VITE_RESEARCH_BLACKLIST}/${pair}` || "/blacklist",
        method: "DELETE",
        invalidatesTags: ["blacklist"],
      }),
      transformResponse: ({ data, message, error }, meta, arg) => {
        if (error && error === 1) {
          notifification("error", message);
        } else {
          notifification("success", message);
        }
        return data;
      },
    }),
  }),
});

// Hooks generated by Redux
export const {
  useGetBlacklistQuery,
  useAddBlacklistItemMutation,
  useDeleteBlacklistItemMutation,
} = blacklistApiSlice;
