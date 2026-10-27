import { createEntityAdapter } from "@reduxjs/toolkit";
import type { FetchBaseQueryError } from "@reduxjs/toolkit/query";
import { toast } from "react-toastify";
import { buildBackUrl, notifification } from "../../utils/api";
import { getToken } from "../../utils/login";
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

export type AlgoRankingItem = {
  name: string;
  count: number;
  bot_profit: number;
};

export const buildGetBotsPath = (
  status: string = BotStatus.ALL,
  startDate: number = weekAgo(),
  endDate: number = new Date().getTime(),
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

type BotOperationResponse = { message: string; error: number; data: Bot };

const streamBotOperation = async (
  url: string,
  operation: string,
): Promise<{ data: BotDetailsState } | { error: FetchBaseQueryError }> => {
  const toastId = toast.info(`${operation} (0%)`, {
    autoClose: false,
    closeOnClick: false,
    hideProgressBar: false,
    progress: 0,
    theme: "colored",
  });
  try {
    const token = getToken();
    const response = await fetch(`${buildBackUrl()}${url}`, {
      method: "POST",
      headers: {
        Accept: "text/event-stream",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    });
    if (!response.ok) {
      throw new Error(`Bot operation failed (HTTP ${response.status})`);
    }
    if (!response.body) {
      throw new Error("The server did not provide a progress stream.");
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let result: BotOperationResponse | undefined;

    const consumeEvent = (block: string) => {
      const lines = block.split("\n");
      const event = lines.find((line) => line.startsWith("event: "))?.slice(7);
      const data = lines
        .filter((line) => line.startsWith("data: "))
        .map((line) => line.slice(6))
        .join("\n");
      if (!event || !data) return;
      const payload = JSON.parse(data);
      if (event === "progress") {
        const percent = Math.max(0, Math.min(100, payload.percent));
        toast.update(toastId, {
          render: `${payload.message} (${percent}%)`,
          progress: percent / 100,
        });
      } else if (event === "result") {
        result = payload.response as BotOperationResponse;
      } else if (event === "error") {
        throw new Error(payload.message);
      }
    };

    while (true) {
      const { value, done } = await reader.read();
      buffer += decoder.decode(value, { stream: !done });
      buffer = buffer.replace(/\r\n/g, "\n");
      let boundary = buffer.indexOf("\n\n");
      while (boundary >= 0) {
        consumeEvent(buffer.slice(0, boundary));
        buffer = buffer.slice(boundary + 2);
        boundary = buffer.indexOf("\n\n");
      }
      if (result || done) break;
    }

    if (!result) {
      throw new Error(
        "The progress stream ended before the result arrived. Refresh the bot before retrying.",
      );
    }
    if (result.error) {
      throw new Error(result.message);
    }
    toast.update(toastId, {
      render: result.message,
      type: "success",
      progress: null,
      autoClose: 5000,
    });
    return { data: { bot: result.data } };
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Bot operation failed";
    toast.update(toastId, {
      render: message,
      type: "error",
      progress: null,
      autoClose: 5000,
    });
    return { error: { status: "CUSTOM_ERROR", error: message } };
  }
};

export const botsApiSlice = userApiSlice.injectEndpoints({
  endpoints: (build) => ({
    getBots: build.query<GetBotsResponse, Partial<GetBotsParams>>({
      query: ({
        status = BotStatus.ALL,
        startDate = undefined,
        endDate = undefined,
      } = {}) => {
        const params = {
          status,
          ...(startDate != null ? { start_date: startDate } : {}),
          ...(endDate != null ? { end_date: endDate } : {}),
        };
        return {
          url: `${import.meta.env.VITE_GET_BOTS}` || "/bots",
          params,
        };
      },
      providesTags: ["bots"],
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
    getOneBySymbol: build.query<SingleBotResponse, string>({
      query: (symbol) => ({
        url: `${import.meta.env.VITE_GET_BOTS}/symbol/${symbol}`,
        method: "GET",
      }),
      providesTags: (result) =>
        result?.bot ? [{ type: "bot", id: result.bot.id }] : [],
      transformResponse: ({ data, message, error }, meta, arg) => {
        if (error && error === 1) {
          notifification("error", message);
        }

        return {
          bot: data,
        };
      },
    }),
    getSingleBot: build.query<SingleBotResponse, string>({
      query: (id) => ({
        url: `${import.meta.env.VITE_GET_BOTS}/${id}`,
        method: "GET",
      }),
      providesTags: (result) =>
        result?.bot ? [{ type: "bot", id: result.bot.id }] : [],
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
        body,
      }),
      invalidatesTags: ["bots"],
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
        body,
      }),
      invalidatesTags: (_result, _error, { id }) => [
        "bots",
        { type: "bot", id },
      ],
      transformResponse: ({ botId, message, error }, meta, arg) => {
        if (error && error === 1) {
          notifification("error", message);
          // Let UI know so we don't navigate
          return null;
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
        body: { ids },
      }),
      invalidatesTags: (_result, _error, ids) => [
        "bots",
        ...ids.map((id) => ({ type: "bot" as const, id })),
      ],
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
    activateBot: build.mutation<BotDetailsState, string>({
      queryFn: (id) =>
        streamBotOperation(
          `${import.meta.env.VITE_ACTIVATE_BOT}/${id}`,
          "Activating bot",
        ),
      invalidatesTags: ["bots", "bot"],
    }),
    deactivateBot: build.mutation<SingleBotResponse, string>({
      queryFn: (id) =>
        streamBotOperation(
          `${import.meta.env.VITE_DEACTIVATE_BOT}/${id}`,
          "Closing bot",
        ),
      invalidatesTags: ["bots", "bot"],
    }),
    getAlgoRanking: build.query<AlgoRankingItem[], void>({
      query: () => ({
        url: import.meta.env.VITE_BOT_ALGO_RANKING || "/bot/algo-ranking",
        method: "GET",
      }),
      transformResponse: (response: { detail: AlgoRankingItem[] }) => {
        return response.detail;
      },
      transformErrorResponse: (error: {
        status: number;
        data: { detail: string };
      }) => {
        if (error.status >= 400) {
          notifification("error", error.data.detail);
        }
        return error;
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
  useActivateBotMutation,
  useDeactivateBotMutation,
  useGetOneBySymbolQuery,
  useGetAlgoRankingQuery,
} = botsApiSlice;
