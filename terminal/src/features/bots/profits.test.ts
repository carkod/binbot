import { BotPosition } from "../../utils/enums";
import { singleBot, type Bot } from "./botInitialState";
import {
  computeSingleBotProfit,
  computeTotalProfit,
  getProfit,
} from "./profits";

const makeBot = (overrides: Partial<Bot> = {}): Bot => ({
  ...singleBot,
  fiat_order_size: 100,
  ...overrides,
  deal: {
    ...singleBot.deal!,
    base_order_size: 100,
    ...overrides.deal,
  },
});

describe("bot profits", () => {
  it("calculates completed long realized PnL percentage against cost basis", () => {
    const bot = makeBot({
      position: BotPosition.LONG,
      deal: {
        ...singleBot.deal!,
        opening_price: 100,
        closing_price: 110,
        closing_qty: 0.5,
      },
    });

    expect(computeSingleBotProfit(bot)).toBe(10);
    expect(computeTotalProfit([bot])).toBe(10);
    expect(getProfit(100, 110, BotPosition.LONG, 0.5)).toBe(10);
  });

  it("inverts completed PnL percentage for shorts", () => {
    const bot = makeBot({
      position: BotPosition.SHORT,
      deal: {
        ...singleBot.deal!,
        opening_price: 100,
        closing_price: 90,
        closing_qty: 0.5,
      },
    });

    expect(computeSingleBotProfit(bot)).toBe(10);
    expect(computeTotalProfit([bot])).toBe(10);
    expect(getProfit(100, 90, BotPosition.SHORT, 0.5)).toBe(10);
  });

  it("keeps live price-move percentage before closing quantity is known", () => {
    const bot = makeBot({
      position: BotPosition.LONG,
      deal: {
        ...singleBot.deal!,
        opening_price: 100,
      },
    });

    expect(computeSingleBotProfit(bot, 110)).toBe(10);
    expect(getProfit(100, 110)).toBe(10);
  });

  it("averages closed price returns and changes when a closed bot is removed", () => {
    const winner = makeBot({
      id: "winner",
      position: BotPosition.LONG,
      deal: {
        ...singleBot.deal!,
        opening_price: 100,
        closing_price: 110,
      },
    });
    const loser = makeBot({
      id: "loser",
      position: BotPosition.SHORT,
      deal: {
        ...singleBot.deal!,
        opening_price: 200,
        closing_price: 210,
      },
    });
    const openBot = makeBot({
      id: "open",
      deal: {
        ...singleBot.deal!,
        opening_price: 100,
        current_price: 200,
      },
    });

    expect(computeTotalProfit([winner, loser, openBot])).toBe(2.5);
    expect(computeTotalProfit([loser, openBot])).toBe(-5);
    expect(computeTotalProfit([openBot])).toBe(0);
  });
});
