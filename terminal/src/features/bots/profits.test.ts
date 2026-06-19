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
});
