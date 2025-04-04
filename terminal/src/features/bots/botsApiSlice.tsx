import { createEntityAdapter } from "@reduxjs/toolkit";
import { notifification } from "../../utils/api";
import { weekAgo } from "../../utils/time";
import { userApiSlice } from "../userApiSlice";
import type { Bot, BotEntity } from "./botInitialState";
import { computeTotalProfit } from "./profits";
import { BotStatus } from "../../utils/enums";
import type {
  CreateBotResponse,
  DefaultBotsResponse,
  EditBotParams,
  SingleBotResponse,
  GetBotsParams,
  BotDetailsState,
} from "./bots";

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
        }

        const totalProfit = computeTotalProfit(data);
        // normalize [] -> {}
        const bots = botsAdapter.setAll(botsAdapter.getInitialState(), data);

        return { bots: bots, totalProfit: totalProfit };
      },
    }),
    getSingleBot: build.query<SingleBotResponse, string>({
      query: (id) => ({
        url: `${import.meta.env.VITE_GET_BOTS}/${id}`,
        method: "GET",
        providesTags: (result) => [{ type: "bot", id: result.bot.id }],
      }),
      transformResponse: ({ data, message, error }, meta, arg) => {
        if (error && error === 1) {
          notifification("error", message);
        }

        return {
          bot: data,
        };
      },
    }),
    createBot: build.mutation<SingleBotResponse, Bot>({
      query: (body) => ({
        url: import.meta.env.VITE_GET_BOTS,
        method: "POST",
        body: body,
        providesTags: (result) => [{ type: "bot", id: body.id }],
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
    editBot: build.mutation<CreateBotResponse, EditBotParams>({
      query: ({ body, id }) => ({
        url: `${import.meta.env.VITE_GET_BOTS}/${id}`,
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
        invalidatesTags: ["bots"],
      }),
      transformResponse: ({ data, message, error }, meta, arg) => {
        if (error && error === 1) {
          notifification("error", message);
        } else {
          notifification("success", message);
        }
        // Return payload to update UI
        return data;
      },
    }),
    activateBot: build.query<BotDetailsState, string>({
      query: (id) => ({
        url: `${import.meta.env.VITE_ACTIVATE_BOT}/${id}`,
        method: "GET",
        invalidatesTags: (result) => [{ type: "bot", id: result.bot.id }],
      }),
      transformResponse: ({ data, message, error }, meta, arg) => {
        if (error && error === 1) {
          notifification("error", message);
        } else {
          notifification("success", message);
        }
        return {
          bot: data,
        }
      },
    }),
    deactivateBot: build.mutation<SingleBotResponse, string>({
      query: (id: string) => ({
        url: `${import.meta.env.VITE_DEACTIVATE_BOT}/${id}`,
        method: "DELETE",
        invalidatesTags: (result) => [{ type: "bot", id: id }],
      }),
      transformResponse: ({ data, message, error }, meta, arg) => {
        if (error && error === 1) {
          notifification("error", message);
        } else {
          notifification("success", message);
        }
        if (data) {
          return {
            bot: data,
          };
        }
        return {
          bot: null,
        };
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
  useLazyActivateBotQuery,
  useDeactivateBotMutation,
} = botsApiSlice;
