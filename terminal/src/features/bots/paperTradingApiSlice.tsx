import { notifification } from "../../utils/api";
import { userApiSlice } from "../userApiSlice";
import type { Bot } from "./botInitialState";
import { computeTotalProfit } from "./profits";
import type {
  CreateBotResponse,
  DefaultBotsResponse,
  EditBotParams,
  GetBotsParams,
  GetBotsResponse,
  SingleBotResponse,
} from "./bots";
import { botsAdapter } from "./botsApiSlice";

export const papertradingApiSlice = userApiSlice.injectEndpoints({
  endpoints: (build) => ({
    getTestBots: build.query<GetBotsResponse, Partial<GetBotsParams>>({
      query: ({ status, startDate, endDate }) => ({
        url: `${import.meta.env.VITE_TEST_BOT}`,
        params: { status, start_date: startDate, end_date: endDate },
        providesTags: (result) => {
          result.bots.map((bot) => ({ type: "paper-trading", id: bot.id }));
        },
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
    getSingleTestBot: build.query<SingleBotResponse, string>({
      query: (id) => ({
        url: `${import.meta.env.VITE_TEST_BOT}/${id}`,
        method: "GET",
        providesTags: (result) => [
          { type: "paper-trading", id: result.bot.id },
        ],
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
    createTestBot: build.mutation<CreateBotResponse, Bot>({
      query: (body) => ({
        url: import.meta.env.VITE_TEST_BOT,
        method: "POST",
        body: body,
        invalidatesTags: (result) => [
          { type: "paper-trading", id: result.bot.id },
        ],
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
    editTestBot: build.mutation<CreateBotResponse, EditBotParams>({
      query: ({ body, id }) => ({
        url: `${import.meta.env.VITE_TEST_BOT}/${id}`,
        method: "PUT",
        body: body,
        invalidatesTags: (result) => [{ type: "paper-trading", id: id }],
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
    deleteTestBot: build.mutation<DefaultBotsResponse, string[]>({
      query: (id) => ({
        url: `${import.meta.env.VITE_TEST_BOT}`,
        method: "DELETE",
        body: id,
        invalidatesTags: (result) => {
          if (id.length) {
            return id.map((id) => ({ type: "paper-trading", id: id }));
          }
        },
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
    activateTestBot: build.query<DefaultBotsResponse, string>({
      query: (id) => ({
        url: `${import.meta.env.VITE_ACTIVATE_TEST_BOT}/${id}`,
        method: "GET",
        invalidatesTags: (result) => [{ type: "paper-trading", id: id }],
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
    deactivateTestBot: build.mutation<DefaultBotsResponse, string>({
      query: (id: string) => ({
        url: `${import.meta.env.VITE_DEACTIVATE_TEST_BOT}/${id}`,
        method: "DELETE",
        invalidatesTags: (result) => [{ type: "paper-trading", id: id }],
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

export const {
  useGetTestBotsQuery,
  useGetSingleTestBotQuery,
  useCreateTestBotMutation,
  useEditTestBotMutation,
  useDeleteTestBotMutation,
  useActivateTestBotQuery,
  useDeactivateTestBotMutation,
  useLazyActivateTestBotQuery,
} = papertradingApiSlice;
