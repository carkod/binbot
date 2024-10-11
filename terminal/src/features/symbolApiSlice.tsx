import { notifification } from "../utils/api"
import { userApiSlice } from "./userApiSlice"

export const symbolsApiSlice = userApiSlice.injectEndpoints({
  endpoints: build => ({
    // No cannibal symbols (without active bots)
    getSymbols: build.query<string[], void>({
      query: () => ({
        url: `${import.meta.env.VITE_NO_CANNIBALISM_SYMBOLS}` || "/symbols",
        providesTags: ["symbols"],
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

export const { useGetSymbolsQuery } = symbolsApiSlice
