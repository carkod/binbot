import { createApi, fetchBaseQuery } from "@reduxjs/toolkit/query/react";
import request, { buildBackUrl } from "../../request";

const baseUrl = buildBackUrl();

export const botsApi = createApi({
  baseQuery: fetchBaseQuery({
    // Fill in your own server starting URL here
    baseUrl: baseUrl,
  }),
  endpoints: (build) => ({
    getBots: build.query({
      query: (params) => {
        let requestURL = `${process.env.REACT_APP_GET_BOTS}`;
        if (params) {
          const { startDate, endDate, status = null } = params;
          const params = `${startDate ? "start_date=" + startDate + "&" : ""}${
            endDate ? "end_date=" + endDate : ""
          }${status ? "&status=" + status : ""}`;
          requestURL += `?${params}`;
        }
        return request(requestURL);
      },
    }),
    getBot: build.query({
      query: (id) => {
        const requestURL = `${process.env.REACT_APP_GET_BOTS}/${id}`;
        return request(requestURL);
      },
    }),
    createBot: build.mutation({
      query: (data) => {
        const requestURL = `${process.env.REACT_APP_GET_BOTS}`;
        return request(requestURL, "POST", data);
      },
    }),
    editBot: build.mutation({
      query: ({ data, id }) => {
        const requestURL = `${process.env.REACT_APP_GET_BOTS}/${id}`;
        return request(requestURL, "PUT", data);
      },
    }),
    deleteBot: build.mutation({
      query: (removeId) => {
        const ids = removeId;
        const params = new URLSearchParams(ids.map((s) => ["id", s]));
        const requestURL = `${
          process.env.REACT_APP_GET_BOTS
        }?${params.toString()}`;
        return request(requestURL, "DELETE");
      },
    }),
    closeBot: build.mutation({
      query: (id) => {
        const requestURL = `${process.env.REACT_APP_DEACTIVATE_BOT}/${id}`;
        return request(requestURL, "DELETE");
      },
    }),
    getSymbols: build.query({
      query: () => {
        const requestURL = `${process.env.REACT_APP_NO_CANNIBALISM_SYMBOLS}`;
        return request(requestURL);
      },
    }),
    getSymbolInfo: build.query({
      query: (pair) => {
        const requestURL = `${process.env.REACT_APP_SYMBOL_INFO}/${pair}`;
        return request(requestURL);
      },
    }),
    activateBot: build.mutation({
      query: (id) => {
        const requestURL = `${process.env.REACT_APP_ACTIVATE_BOT}/${id}`;
        return request(requestURL);
      },
    }),
    deactivateBot: build.mutation({
      query: (id) => {
        const requestURL = `${process.env.REACT_APP_DEACTIVATE_BOT}/${id}`;
        return request(requestURL, "DELETE");
      },
    }),
    getCandlestick: build.query({
      query: ({ pair, interval }) => {
        const requestURL = `${process.env.REACT_APP_CANDLESTICK}?symbol=${pair}&interval=${interval}`;
        return request(requestURL);
      },
    }),
    archiveBot: build.mutation({
      query: (id) => {
        const requestURL = `${process.env.REACT_APP_ARCHIVE_BOT}/${id}`;
        return request(requestURL, "PUT");
      },
    }),
    getSettings: build.query({
      query: () => {
        const url = new URL(process.env.REACT_APP_RESEARCH_CONTROLLER, baseUrl);
        return request(url);
      },
    }),
    editSettings: build.mutation({
      query: (data) => {
        const url = new URL(process.env.REACT_APP_RESEARCH_CONTROLLER, baseUrl);
        return request(url, "PUT", data);
      },
    }),
  }),
});
