import { singleBot, type Bot } from "../../features/bots/botInitialState";
import { BotPosition, BotStatus, MarketType, QuoteAsset } from "../enums";
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
  it("flips futures order, trailing, and stop-loss previews with position", () => {
    const bot: Bot = {
      ...singleBot,
      market_type: MarketType.FUTURES,
      quote_asset: QuoteAsset.USDT,
      fiat_order_size: 25,
      status: BotStatus.INACTIVE,
      trailing: true,
      trailing_profit: 6,
      trailing_deviation: 4,
      stop_loss: 3,
    };
    const price = 100;
    const line = (lines: ReturnType<typeof updateOrderLines>, id: string) =>
      lines.find((orderLine) => orderLine.id === id);

    const longLines = updateOrderLines(bot, price);
    const shortLines = updateOrderLines(
      { ...bot, position: BotPosition.SHORT },
      price,
    );

    expect(line(longLines, "base_order")).toMatchObject({
      text: "Base",
      price: 100,
    });
    expect(line(shortLines, "base_order")).toMatchObject({
      text: "Base (Margin sell)",
      price: 100,
    });
    expect(line(longLines, "trailing_profit")?.price).toBeCloseTo(106);
    expect(line(shortLines, "trailing_profit")?.price).toBeCloseTo(94);
    expect(line(longLines, "trailing_stop_loss")?.price).toBeCloseTo(
      106 * 0.96,
    );
    expect(line(shortLines, "trailing_stop_loss")?.price).toBeCloseTo(
      94 * 1.04,
    );
    expect(line(longLines, "stop_loss")?.price).toBeCloseTo(97);
    expect(line(shortLines, "stop_loss")?.price).toBeCloseTo(103);
  });

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
