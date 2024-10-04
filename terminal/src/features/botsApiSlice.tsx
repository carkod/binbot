
import { createApi } from "@reduxjs/toolkit/query/react"
import {
  baseQuery,
} from "../utils/api"

interface LoginCredentials {
  email: string
  password: string
}

interface BotsResponse {
  data?: string
  error?: number
}

// Define a service using a base URL and expected endpoints
export const botsApiSlice = createApi({
  baseQuery: baseQuery,
  reducerPath: "botsApi",
  // Tag types are used for caching and invalidation.
  tagTypes: ["bots"],
  endpoints: build => ({
    getBots: build.query<BotsResponse, void>({
      query: () => ({
        url: import.meta.env.VITE_GET_BOTS || "/bots",
        method: "GET",
      }),
    }),
    getSingleBot: build.query<BotsResponse, string>({
      query: (id: string) => ({
        url: `${import.meta.env.VITE_GET_BOTS}/${id}` || "/bot",
        method: "GET",
      }),
    }),
    createBot: build.mutation<BotsResponse, LoginCredentials>({
      query: body => ({
          url: import.meta.env.VITE_GET_BOTS || "/bot",
          method: "POST",
          body: body,
          invalidatesTags: ["bots"]
      }),
    }),
    editBot: build.mutation<BotsResponse, LoginCredentials>({
      query: body => ({
          url: import.meta.env.VITE_GET_BOTS || "/bot",
          method: "PUT",
          body: body,
          invalidatesTags: ["bots"]
      }),
    }),
    deleteBot: build.mutation<BotsResponse, string>({
      query: (id: string) => ({
          url: `${import.meta.env.VITE_GET_BOTS}/${id}` || "/bot",
          method: "DELETE",
          invalidatesTags: ["bots"]
      }),
    }),
    activateBot: build.query<BotsResponse, string>({
      query: (id: string) => ({
          url: `${import.meta.env.VITE_ACTIVATE_BOT}/${id}` || "/bot/activate",
          method: "GET",
          invalidatesTags: ["bots"]
      }),
    }),
    deactivateBot: build.query<BotsResponse, string>({
      query: (id: string) => ({
          url: `${import.meta.env.VITE_DEACTIVATE_BOT}/${id}` || "/bot/deactivate",
          method: "GET",
          invalidatesTags: ["bots"]
      }),
    }),
  }),
})

export const {
  useGetBotsQuery,
  useGetSingleBotQuery,
  useCreateBotMutation,
  useEditBotMutation,
  useDeleteBotMutation,
  useActivateBotQuery,
  useDeactivateBotQuery,
} = botsApiSlice
