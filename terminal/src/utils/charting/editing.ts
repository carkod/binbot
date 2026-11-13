import type { Bot } from "../../features/bots/botInitialState";
import { BotPosition, BotStatus, EntryMode, MarketType } from "../enums";

export type OrderLineField =
  "stop_loss" | "entry_price" | "trailing_profit" | "trailing_deviation";

export type ChartEditField = OrderLineField | "entry_expires_at";

export function canEditConditionalEntry(bot: Bot): boolean {
  return (
    bot.market_type === MarketType.FUTURES &&
    bot.entry_mode === EntryMode.CONDITIONAL_LIMIT &&
    bot.status === BotStatus.INACTIVE &&
    !bot.orders?.length
  );
}

export const fieldOrderLines: Record<OrderLineField, string> = {
  stop_loss: "stop_loss",
  entry_price: "entry_price",
  trailing_profit: "trailing_profit",
  trailing_deviation: "trailing_stop_loss",
};

export function entryReferencePrice(bot: Bot, currentPrice: number): number {
  return (
    bot.deal?.opening_price ||
    (bot.entry_mode === EntryMode.CONDITIONAL_LIMIT ? bot.entry_price : 0) ||
    currentPrice
  );
}

export function percentageFromOrderLine(
  field: Exclude<OrderLineField, "entry_price">,
  price: number,
  reference: number,
  position: BotPosition,
): number | null {
  if (
    !Number.isFinite(price) ||
    price <= 0 ||
    !Number.isFinite(reference) ||
    reference <= 0
  )
    return null;
  const direction = position === BotPosition.SHORT ? -1 : 1;
  const percentage =
    100 *
    direction *
    (field === "trailing_profit"
      ? price / reference - 1
      : 1 - price / reference);
  return percentage >= 0 && percentage < 100
    ? Math.round(percentage * 1e8) / 1e8
    : null;
}
