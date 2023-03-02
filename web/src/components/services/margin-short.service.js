import { dealColors } from "./charting.service";

export default function marginTrading(bot, currentPrice) {
  let totalOrderLines = [];
  currentPrice = parseFloat(currentPrice)
  if (bot.deal.buy_back_price && bot.deal.buy_back_price > 0) {
    // If there is sell_price, it means it's completed
    totalOrderLines.push({
      id: "base_order",
      text: "Base (Margin sell)",
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
      text: `Take profit ${bot.take_profit}% (Margin buy)`,
      tooltip: [bot.status, " Margin buy"],
      quantity: `${bot.base_order_size} ${bot.quoteAsset}`,
      price: bot.deal.buy_back_price, // buy_profit * take_profit%
      color: dealColors.take_profit,
    });
  } else {
    const price = bot.deal.margin_short_sell_price > 0 ? bot.deal.margin_short_sell_price : currentPrice;
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
      price: parseFloat(price),
      color: dealColors.base_order,
    });
    totalOrderLines.push({
      id: "take_profit",
      text: `Take profit ${bot.take_profit}% (Margin)`,
      tooltip: [bot.status, " Sell Order "],
      quantity: `${bot.base_order_size} ${bot.quoteAsset}`,
      price: price - ( price * parseFloat(bot.take_profit) / 100), // buy_profit * take_profit%
      color: dealColors.take_profit,
    });
  }

  if (bot.stop_loss && parseFloat(bot.stop_loss) > 0) {
    let stopLossPrice = 0;
    if (bot.deal.stop_loss_price) {
      stopLossPrice =
        bot.deal.stop_loss_price;
    } else {
      stopLossPrice = currentPrice * (1 + (parseFloat(bot.stop_loss) / 100));
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
