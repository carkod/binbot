import { type BotStatus } from "../../utils/enums";
import type { Bot } from "./botInitialState";

export interface DefaultBotsResponse {
  error: number;
  data?: string;
  message?: string;
}

export interface GetBotsParams {
  status?: BotStatus;
  startDate?: number;
  endDate?: number;
  symbol?: string;
}

export interface SingleBotResponse {
  bot: Bot | null;
}

export interface EditBotParams {
  body: Bot;
  id: string;
}

export interface BotDetailsFormField {
  name: string;
  value: string | number;
}

export interface BotDetailsFormFieldBoolean {
  name: string;
  value: boolean;
}

export interface BotDetailsState {
  bot: Bot;
}
