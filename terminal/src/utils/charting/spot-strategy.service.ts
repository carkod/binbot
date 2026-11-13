import { entryReferencePrice } from "./editing";
import { type OrderLine } from "./index.d";
import { type Bot } from "../../features/bots/botInitialState";
import { dealColors } from "../../utils/charting/index";
import {
  BotStatus,
  EntryMode,
  DealType,
  MarketType,
  QuoteAsset,
} from "../enums";

const getBaseOrderQuoteAsset = (bot: Bot): number => {
  let baseOrderSize = 0;
  bot.orders.forEach((element) => {
    if (element.deal_type === DealType.CONVERSION) {
      baseOrderSize = element.qty;
    }
  });
  return baseOrderSize;
};

export default function spotTrading(
  bot: Bot,
  currentPrice: number = 0,
  previewTrailingSettings = false,
  previewStopLossSettings = false,
): OrderLine[] {
  const quoteAsset = bot.quote_asset;
  const price = entryReferencePrice(bot, currentPrice);
  let totalOrderLines: OrderLine[] = [];
  let baseOrderSize = 0;

  if (
    bot.market_type === MarketType.FUTURES ||
    quoteAsset === QuoteAsset.USDC
  ) {
    baseOrderSize =
      bot.deal.base_order_size > 0
        ? bot.deal.base_order_size
        : bot.fiat_order_size;
  } else {
    baseOrderSize =
      bot.deal.base_order_size > 0
        ? bot.deal.base_order_size
        : getBaseOrderQuoteAsset(bot);
  }

  if (baseOrderSize > 0 && currentPrice) {
    const qtyText =
      bot.deal.opening_qty > 0
        ? String(bot.deal.opening_qty)
        : String(baseOrderSize);
    if (bot.deal.closing_price > 0) {
      // If there is closing_price, it means it's completed
      totalOrderLines.push({
        id: "base_order",
        text: "Base",
        tooltip: [
          bot.status,
          `${
            bot.deal.opening_qty > 0
              ? `${bot.deal.opening_qty} ${quoteAsset}`
              : ""
          }`,
        ],
        quantity: `${qtyText} ${quoteAsset}`,
        price: bot.deal.opening_price,
        color: dealColors.base_order,
      });
    } else {
      // if no closing_price
      // bot inactive: currentPrice, bot active: opening_price
      totalOrderLines.push({
        id: "base_order",
        text: "Base",
        tooltip: [
          bot.status,
          `${
            bot.deal.opening_qty && bot.deal.opening_qty > 0
              ? `${bot.deal.opening_qty} ${quoteAsset}`
              : ""
          }`,
        ],
        quantity: `${qtyText} ${quoteAsset}`,
        price: price,
        color: dealColors.base_order,
      });
    }

    if (
      bot.trailing &&
      (previewTrailingSettings ||
        (bot.trailing_deviation > 0 && bot.trailing_profit > 0))
    ) {
      // Bot is sold and completed
      if (bot.status === BotStatus.COMPLETED && bot.deal.closing_price > 0) {
        totalOrderLines.push({
          id: "trailing_stop_loss",
          text: `Trailing stop loss -${bot.trailing_deviation}%`,
          tooltip: [bot.status, " Sell when prices drop to here"],
          quantity: `${qtyText} ${quoteAsset}`,
          price: bot.deal.closing_price,
          color: dealColors.trailing_stop_loss,
        });
        totalOrderLines.push({
          id: "trailing_profit",
          text: `Trailing profit ${bot.trailing_profit}%`,
          tooltip: [bot.status, " Breakpoint to move up trailing profit"],
          quantity: `${qtyText} ${quoteAsset}`,
          price: bot.deal.trailing_profit_price || bot.deal.closing_price,
          color: dealColors.trailing_profit,
          lineStyle: 2,
        });
      } else if (
        bot.deal.opening_price > 0 &&
        bot.status === BotStatus.ACTIVE
      ) {
        const trailingProfitPrice = previewTrailingSettings
          ? bot.deal.opening_price * (1 + bot.trailing_profit / 100)
          : bot.deal.trailing_profit_price;
        totalOrderLines.push({
          id: "trailing_profit",
          text: `Trail profit ${bot.trailing_profit}%`,
          tooltip: [bot.status, " Trace upward profit"],
          quantity: `${qtyText} ${quoteAsset}`,
          price: trailingProfitPrice,
          color: dealColors.trailing_profit,
        });
        if (previewTrailingSettings || bot.deal.trailing_stop_loss_price > 0) {
          totalOrderLines.push({
            id: "trailing_stop_loss",
            text: `Trailing stop loss ${bot.trailing_deviation}%`,
            tooltip: [bot.status, " Sell order when prices drop here"],
            quantity: `${qtyText} ${quoteAsset}`,
            price: previewTrailingSettings
              ? trailingProfitPrice * (1 - bot.trailing_deviation / 100)
              : bot.deal.trailing_stop_loss_price,
            color: dealColors.trailing_stop_loss,
          });
        }
      } else {
        // Inactive bot
        const trailingProfitPrice = price * (1 + bot.trailing_profit / 100);
        totalOrderLines.push({
          id: "trailing_profit",
          text: `Trailing profit ${bot.trailing_profit}%`,
          tooltip: [bot.status, " Breakpoint to increase Take profit"],
          quantity: `${qtyText} ${quoteAsset}`,
          price: trailingProfitPrice,
          color: dealColors.trailing_profit,
          lineStyle: 2,
        });
        totalOrderLines.push({
          id: "trailing_stop_loss",
          text: `Trailing stop loss -${bot.trailing_deviation}%`,
          tooltip: [bot.status, " Sell order when prices drop here"],
          quantity: `${bot.deal.opening_qty || baseOrderSize} ${quoteAsset}`,
          price: trailingProfitPrice * (1 - bot.trailing_deviation / 100),
          color: dealColors.trailing_stop_loss,
        });
      }
    } else {
      // No trailing, just normal take_profit
      if (
        bot.status === BotStatus.COMPLETED &&
        bot.deal.take_profit_price > 0
      ) {
        totalOrderLines.push({
          id: "take_profit",
          text: `Take profit ${bot.take_profit}%`,
          tooltip: [bot.status, " Sell Order "],
          quantity: `${qtyText} ${quoteAsset}`,
          price: bot.deal.take_profit_price, // this makes sure we use the real-time price
          color: dealColors.take_profit,
        });
      } else {
        if (!bot.trailing) {
          totalOrderLines.push({
            id: "take_profit",
            text: `Take profit ${bot.take_profit}%`,
            tooltip: [bot.status, " Sell Order "],
            quantity: `${qtyText} ${quoteAsset}`,
            price: currentPrice * (1 + bot.take_profit / 100), // buy_profit * take_profit%
            color: dealColors.take_profit,
          });
        }
      }
    }

    // Stop loss remains the same in all situations
    if (bot.stop_loss > 0 || previewStopLossSettings) {
      const stop_loss = previewStopLossSettings
        ? price * (1 - bot.stop_loss / 100)
        : bot.deal.stop_loss_price || price * (1 - bot.stop_loss / 100);
      totalOrderLines.push({
        id: "stop_loss",
        text: `Stop Loss ${bot.stop_loss}%`,
        tooltip: [bot.status, " Sell Order "],
        quantity: `${qtyText} ${quoteAsset}`,
        price: stop_loss,
        color: dealColors.stop_loss,
      });
    }
  }
  if (
    bot.entry_mode === EntryMode.CONDITIONAL_LIMIT &&
    bot.entry_price > 0 &&
    (bot.status === BotStatus.INACTIVE || bot.status === BotStatus.PENDING)
  ) {
    totalOrderLines.push({
      id: "entry_price",
      text: "Conditional entry limit",
      tooltip: [bot.status, `Entry limit ${bot.entry_price} ${bot.fiat}`],
      quantity:
        bot.deal.base_order_size > 0
          ? `${bot.deal.base_order_size} contracts`
          : `${bot.fiat_order_size} ${bot.fiat}`,
      price: bot.entry_price,
      color: dealColors.entry_price,
      lineStyle: 2,
    });
  }

  return totalOrderLines;
}
