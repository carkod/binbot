import { dealColors } from "./charting.service";

export default function marginTrading(bot, currentPrice) {
  let totalOrderLines = [];

  if (bot.deal.buy_back_price && bot.deal.buy_back_price > 0) {
    // If there is sell_price, it means it's completed
    totalOrderLines.push({
      id: "base_order",
      text: "Base",
      tooltip: [
        bot.status,
        `${
          bot.deal.buy_total_qty > 0
            ? bot.deal.buy_total_qty + bot.quoteAsset + "(Avg total)"
            : ""
        }`,
      ],
      quantity: `${bot.base_order_size} ${bot.quoteAsset}`,
      price: parseFloat(bot.deal.margin_short_sell_price),
      color: dealColors.base_order,
    });
    totalOrderLines.push({
      id: "take_profit",
      text: `Take profit ${bot.take_profit}% (Margin)`,
      tooltip: [bot.status, " Sell Order "],
      quantity: `${bot.base_order_size} ${bot.quoteAsset}`,
      price: bot.deal.buy_back_price, // buy_profit * take_profit%
      color: dealColors.take_profit,
    });
  } else {
    totalOrderLines.push({
      id: "base_order",
      text: "Base",
      tooltip: [
        bot.status,
        `${
          bot.deal.buy_total_qty > 0
            ? bot.deal.buy_total_qty + bot.quoteAsset + "(Avg total)"
            : ""
        }`,
      ],
      quantity: `${bot.base_order_size} ${bot.quoteAsset}`,
      price: parseFloat(currentPrice),
      color: dealColors.base_order,
    });
    totalOrderLines.push({
      id: "take_profit",
      text: `Take profit ${bot.take_profit}% (Margin)`,
      tooltip: [bot.status, " Sell Order "],
      quantity: `${bot.base_order_size} ${bot.quoteAsset}`,
      price: currentPrice - ( currentPrice * parseFloat(bot.take_profit) / 100), // buy_profit * take_profit%
      color: dealColors.take_profit,
    });
  }

  if (bot.stop_loss && bot.stop_loss > 0) {
    let stopLossPrice = 0;
    if (bot.deal.margin_short_buy_back_price) {
      stopLossPrice =
        bot.deal.margin_short_stop_loss_price;
    } else {
      stopLossPrice = currentPrice * (1 + (bot.stop_loss / 100));
    }
    // Stop loss
    totalOrderLines.push({
      id: "stop_loss",
      text: `Stop Loss ${bot.stop_loss}%`,
      tooltip: [bot.status, " Sell Order "],
      quantity: `${bot.base_order_size} ${bot.quoteAsset}`,
      price: stopLossPrice, // buy_profit * take_profit%
      color: "red",
    });
  }

  return totalOrderLines;
}
