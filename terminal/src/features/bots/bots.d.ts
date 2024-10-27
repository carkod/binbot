import type { EntityId, EntityState } from "@reduxjs/toolkit";

export interface DefaultBotsResponse {
  error: number;
  data?: string;
  message?: string;
}
export interface GetBotsResponse {
  bots: EntityState<Bot, EntityId>;
  totalProfit: number;
}

export interface GetBotsParams {
  status?: string;
  startDate?: number;
  endDate?: number;
}

export interface SingleBotResponse {
  bot: Bot;
}

export interface CreateBotResponse extends DefaultBotsResponse {
  botId: string;
}

export interface EditBotParams {
  body: Bot;
  id: string;
}

export interface BotsState {
  bots: Bot[];
  totalProfit: number;
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
