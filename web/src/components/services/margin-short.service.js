import { dealColors } from "./charting.service";

export default function marginTrading(bot, currentPrice) {
  let totalOrderLines = [];

  //   if (bot.base_order_size && currentPrice) {
  //     if (bot.deal.original_buy_price && bot.deal.original_buy_price > 0) {
  //       totalOrderLines.push({
  //         id: "original_buy_price",
  //         text: "Original buy price",
  //         tooltip: [bot.status, " Original buy price before SO triggered"],
  //         quantity: `${bot.base_order_size} ${bot.quoteAsset}`,
  //         price: parseFloat(bot.deal.original_buy_price),
  //         color: dealColors.base_order,
  //       });
  //     }
  //   }

  if (bot.deal.sell_price && bot.deal.sell_price > 0) {
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
      price: parseFloat(bot.deal.buy_price),
      color: dealColors.base_order,
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
    if (bot.deal.buy_price) {
      stopLossPrice =
        bot.deal.buy_price * (1 + (bot.stop_loss / 100));
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
