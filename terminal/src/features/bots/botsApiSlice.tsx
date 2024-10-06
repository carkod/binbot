import {
  createEntityAdapter,
  type EntityId,
  type EntityState
} from "@reduxjs/toolkit"
import { notifification } from "../../utils/api"
import { weekAgo } from "../../utils/time"
import { userApiSlice } from "../userApiSlice"
import type { Bot } from "./botInitialState"
import { computeTotalProfit } from "./profits"

interface DefaultBotsResponse {
  error: number
  data?: string
  message?: string
}
interface GetBotsResponse {
  bots: EntityState<Bot, EntityId>
  totalProfit: number
}

interface GetBotsParams {
  status?: string
  startDate?: number
  endDate?: number
}

export const buildGetBotsPath = (
  status: string = null,
  startDate: number = weekAgo(),
  endDate: number = new Date().getTime(),
): string => {
  const params = new URLSearchParams({
    start_date: startDate.toString(),
    end_date: endDate.toString(),
    status: status,
  })
  return params.toString()
}

const botsAdapter = createEntityAdapter<Bot>({
  sortComparer: (a, b) => a.status.localeCompare(b.status),
})

export const botsApiSlice = userApiSlice.injectEndpoints({
  endpoints: build => ({
    getBots: build.query<GetBotsResponse, Partial<GetBotsParams>>({
      query: ({ status, startDate, endDate }) => ({
        url: `${import.meta.env.VITE_GET_BOTS}` || "/bots",
        params: { status, start_date: startDate, end_date: endDate },
        providesTags: ["bots"],
      }),
      transformResponse: ({ data, message, error }, meta, arg) => {
        if (error && error === 1) {
          notifification("error", message)
        } else {
          notifification("success", message)
        }

        const totalProfit = computeTotalProfit(data)

        const bots = botsAdapter.setAll(botsAdapter.getInitialState(), data)

        return { bots: bots, totalProfit: totalProfit }
      },
    }),
    getSingleBot: build.query<DefaultBotsResponse, string>({
      query: id => ({
        url: `${import.meta.env.VITE_GET_BOTS}/${id}` || "/bot",
        method: "GET",
      }),
      transformResponse: ({ data, message, error }, meta, arg) => {
        if (error && error === 1) {
          notifification("error", message)
        } else {
          notifification("success", message)
        }
        return data
      }
    }),
    createBot: build.mutation<DefaultBotsResponse, Bot>({
      query: body => ({
        url: import.meta.env.VITE_GET_BOTS || "/bot",
        method: "POST",
        body: body,
        invalidatesTags: ["bots"],
      }),
    }),
    editBot: build.mutation<DefaultBotsResponse, Bot>({
      query: body => ({
        url: import.meta.env.VITE_GET_BOTS || "/bot",
        method: "PUT",
        body: body,
        invalidatesTags: ["bots"],
      }),
    }),
    deleteBot: build.mutation<DefaultBotsResponse, string[]>({
      query: id => ({
        url: `${import.meta.env.VITE_GET_BOTS}` || "/bot",
        method: "DELETE",
        body: id,
        invalidatesTags: ["bots"],
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
    activateBot: build.query<DefaultBotsResponse, string>({
      query: (id: string) => ({
        url: `${import.meta.env.VITE_ACTIVATE_BOT}/${id}` || "/bot/activate",
        method: "GET",
      }),
    }),
    deactivateBot: build.mutation<DefaultBotsResponse, string>({
      query: (id: string) => ({
        url:
          `${import.meta.env.VITE_DEACTIVATE_BOT}/${id}` || "/bot/deactivate",
        method: "GET",
      }),
    }),
  }),
})

export interface BotsState {
  bots: Bot[]
  totalProfit: number
}

// Hooks generated by Redux
export const {
  useGetBotsQuery,
  useGetSingleBotQuery,
  useCreateBotMutation,
  useEditBotMutation,
  useDeleteBotMutation,
  useActivateBotQuery,
  useDeactivateBotMutation,
} = botsApiSlice
