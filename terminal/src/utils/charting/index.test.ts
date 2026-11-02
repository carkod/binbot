import { singleBot, type Bot } from "../../features/bots/botInitialState";
import {
  BotPosition,
  BotStatus,
  DealType,
  MarketType,
  QuoteAsset,
} from "../enums";
import { updateOrderLines, updateTimescaleMarks } from "./index";

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
  it("shows a non-trailing short take-profit below the base order", () => {
    const bot: Bot = {
      ...singleBot,
      market_type: MarketType.MARGIN,
      position: BotPosition.SHORT,
      fiat_order_size: 25,
      trailing: false,
      take_profit: 6.5,
    };
    const inactiveLines = updateOrderLines(bot, 100);

    expect(inactiveLines.find((line) => line.id === "base_order")?.price).toBe(
      100,
    );
    expect(
      inactiveLines.find((line) => line.id === "take_profit"),
    ).toMatchObject({
      text: "Take profit 6.5% (Margin)",
      price: 93.5,
    });

    const activeLines = updateOrderLines(
      {
        ...bot,
        status: BotStatus.ACTIVE,
        deal: {
          ...singleBot.deal!,
          opening_price: 100,
          take_profit_price: 92,
        },
      },
      101,
    );
    expect(activeLines.find((line) => line.id === "take_profit")?.price).toBe(
      92,
    );
  });

  it("previews changed trailing percentages for an active long and short", () => {
    const bot: Bot = {
      ...singleBot,
      status: BotStatus.ACTIVE,
      fiat_order_size: 25,
      trailing: true,
      trailing_profit: 5,
      trailing_deviation: 4,
      deal: {
        ...singleBot.deal!,
        opening_price: 100,
        trailing_profit_price: 103,
        trailing_stop_loss_price: 101,
      },
    };
    const actual = updateOrderLines(bot, 100);
    const shortActual = updateOrderLines(
      { ...bot, position: BotPosition.SHORT },
      100,
    );
    const longPreview = updateOrderLines(bot, 100, true);
    const shortPreview = updateOrderLines(
      { ...bot, position: BotPosition.SHORT },
      100,
      true,
    );
    const price = (lines: ReturnType<typeof updateOrderLines>, id: string) =>
      lines.find((line) => line.id === id)?.price;

    expect(price(actual, "trailing_profit")).toBe(103);
    expect(price(actual, "trailing_stop_loss")).toBe(101);
    expect(
      shortActual.find((line) => line.id === "trailing_profit")?.text,
    ).toBe("Trail profit 5%");
    expect(price(longPreview, "trailing_profit")).toBe(105);
    expect(price(longPreview, "trailing_stop_loss")).toBeCloseTo(100.8);
    expect(price(shortPreview, "trailing_profit")).toBe(95);
    expect(price(shortPreview, "trailing_stop_loss")).toBeCloseTo(98.8);
    expect(
      shortPreview.find((line) => line.id === "trailing_profit")?.text,
    ).toBe("Trail profit 5%");
  });

  it("omits cancelled orders from timescale marks", () => {
    const orders = ["CANCELED", "CANCELLED", "FILLED"].map((status) => ({
      order_id: status,
      deal_type: DealType.STOP_LOSS,
      status,
      price: 100,
      qty: 1,
      timestamp: "1700000000000",
    }));

    expect(
      updateTimescaleMarks({ ...singleBot, orders }).map((mark) => mark.id),
    ).toEqual(["FILLED"]);
  });

  it("matches stop-loss and trailing-stop colors on lines and timescale marks", () => {
    const orders = [
      DealType.STOP_LOSS,
      DealType.TRAILING_STOP_LOSS,
      DealType.BASE_ORDER,
    ].map((deal_type) => ({
      order_id: deal_type,
      deal_type,
      price: 100,
      qty: 1,
      timestamp: "1700000000000",
    }));

    for (const position of [BotPosition.LONG, BotPosition.SHORT]) {
      const bot: Bot = {
        ...singleBot,
        market_type: MarketType.FUTURES,
        position,
        fiat_order_size: 25,
        trailing: true,
        trailing_profit: 6,
        trailing_deviation: 4,
        orders,
      };
      const lines = updateOrderLines(bot, 100);
      const marks = updateTimescaleMarks(bot);

      expect(lines.find((line) => line.id === DealType.STOP_LOSS)?.color).toBe(
        "red",
      );
      expect(marks.find((mark) => mark.id === DealType.STOP_LOSS)?.color).toBe(
        "red",
      );
      expect(
        lines.find((line) => line.id === DealType.TRAILING_STOP_LOSS)?.color,
      ).toBe("#87cb16");
      expect(
        marks.find((mark) => mark.id === DealType.TRAILING_STOP_LOSS)?.color,
      ).toBe("#87cb16");
      expect(marks.find((mark) => mark.id === DealType.BASE_ORDER)?.color).toBe(
        lines.find((line) => line.id === DealType.BASE_ORDER)?.color,
      );
    }
  });

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
