import type { FetchBaseQueryError } from "@reduxjs/toolkit/query";
import type { Bot } from "../features/bots/botInitialState";
import type { BotDetailsState } from "../features/bots/bots";

export interface StandardResponse {
  data: any;
  message: string;
  error: number;
}

export interface BotOperationResponse {
  message: string;
  error: number;
  data: Bot;
}

export type BotOperationStreamResult =
  { data: BotDetailsState } | { error: FetchBaseQueryError };
