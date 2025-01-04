import { createEntityAdapter } from "@reduxjs/toolkit";
import { notifification } from "../../utils/api";
import { weekAgo } from "../../utils/time";
import { userApiSlice } from "../userApiSlice";
import type { Bot, BotEntity } from "./botInitialState";
import { computeTotalProfit } from "./profits";
import { BotStatus } from "../../utils/enums";
import { type GetBotsParams } from "./bots";

type GetBotsResponse = {
  bots: BotEntity;
  totalProfit: number;
};

export const buildGetBotsPath = (
  status: string = BotStatus.ALL,
  startDate: number = weekAgo(),
  endDate: number = new Date().getTime()
): string => {
  const params = new URLSearchParams({
    start_date: startDate.toString(),
    end_date: endDate.toString(),
    status: status,
  });
  return params.toString();
};

export const botsAdapter = createEntityAdapter<Bot>({
  sortComparer: false,
});

export const botsApiSlice = userApiSlice.injectEndpoints({
  endpoints: (build) => ({
    getBots: build.query<GetBotsResponse, Partial<GetBotsParams>>({
      query: ({ status, startDate, endDate }) => ({
        url: `${import.meta.env.VITE_GET_BOTS}` || "/bots",
        params: { status, start_date: startDate, end_date: endDate },
        providesTags: ["bots"],
      }),
      transformResponse: ({ data, message, error }, meta, arg) => {
        if (error && error === 1) {
          notifification("error", message);
        } else {
          notifification("success", message);
        }

        const totalProfit = computeTotalProfit(data);
        // normalize [] -> {}
        const bots = botsAdapter.setAll(botsAdapter.getInitialState(), data);

        return { bots: bots, totalProfit: totalProfit };
      },
    }),
    getSingleBot: build.query<SingleBotResponse, string>({
      query: (id) => ({
        url: `${import.meta.env.VITE_GET_BOTS}/${id}` || "/bot",
        method: "GET",
        providesTags: (result) => [{ type: "bot", id: result.bot.id }],
      }),
      transformResponse: ({ data, message, error }, meta, arg) => {
        if (error && error === 1) {
          notifification("error", message);
        } else {
          notifification("success", message);
        }
        return {
          bot: data,
        };
      },
    }),
    createBot: build.mutation<CreateBotResponse, Bot>({
      query: (body) => ({
        url: import.meta.env.VITE_GET_BOTS || "/bot",
        method: "POST",
        body: body,
        providesTags: (result) => [{ type: "bot", id: id }],
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
    editBot: build.mutation<CreateBotResponse, EditBotParams>({
      query: ({ body, id }) => ({
        url: `${import.meta.env.VITE_GET_BOTS}/${id}` || "/bot",
        method: "PUT",
        body: body,
        invalidatesTags: (result) => [{ type: "bot", id: id }],
      }),
      transformResponse: ({ botId, message, error }, meta, arg) => {
        if (error && error === 1) {
          notifification("error", message);
        } else {
          notifification("success", message);
        }
        return botId;
      },
    }),
    deleteBot: build.mutation<DefaultBotsResponse, string[]>({
      query: (ids) => ({
        url: `${import.meta.env.VITE_GET_BOTS}` || "/bot",
        method: "DELETE",
        body: ids,
        invalidatesTags: ["bots"]
      }),
      transformResponse: ({ botId, message, error }, meta, arg) => {
        if (error && error === 1) {
          notifification("error", message);
        } else {
          notifification("success", message);
        }
        // Return payload to update UI
        return arg;
      },
    }),
    activateBot: build.query<DefaultBotsResponse, string>({
      query: (id) => ({
        url: `${import.meta.env.VITE_ACTIVATE_BOT}/${id}` || "/bot/activate",
        method: "GET",
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
    deactivateBot: build.mutation<DefaultBotsResponse, string>({
      query: (id: string) => ({
        url:
          `${import.meta.env.VITE_DEACTIVATE_BOT}/${id}` || "/bot/deactivate",
        method: "DELETE",
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
  useGetBotsQuery,
  useGetSingleBotQuery,
  useCreateBotMutation,
  useEditBotMutation,
  useDeleteBotMutation,
  useActivateBotQuery,
  useDeactivateBotMutation,
} = botsApiSlice;
