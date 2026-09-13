import { singleBot, type Bot } from "../../features/bots/botInitialState";
import { BotPosition, BotStatus, MarketType } from "../enums";
import { updateOrderLines } from "./index";

function completedTrailingFuturesLong(): Bot {
  return {
    ...singleBot,
    market_type: MarketType.FUTURES,
    position: BotPosition.LONG,
    status: BotStatus.COMPLETED,
    trailing: true,
    trailing_profit: 6,
    trailing_deviation: 4,
    deal: {
      ...singleBot.deal!,
      base_order_size: 6,
      opening_price: 0.01146,
      opening_qty: 6,
      closing_price: 0.0103,
      closing_qty: 6,
      trailing_profit_price: 0.01214,
      trailing_stop_loss_price: 0.0103,
    },
  };
}

describe("chart order lines", () => {
  it("uses the persisted trailing-profit trigger for a completed futures long", () => {
    const lines = updateOrderLines(completedTrailingFuturesLong(), 0.01052);

    expect(lines.find((line) => line.id === "trailing_profit")?.price).toBe(
      0.01214,
    );
    expect(lines.find((line) => line.id === "trailing_stop_loss")?.price).toBe(
      0.0103,
    );
  });

  it("falls back to the closing price for legacy deals without a trailing-profit price", () => {
    const bot = completedTrailingFuturesLong();
    bot.deal!.trailing_profit_price = 0;

    const lines = updateOrderLines(bot, 0.01052);

    expect(lines.find((line) => line.id === "trailing_profit")?.price).toBe(
      0.0103,
    );
  });
});
