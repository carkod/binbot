import { BotPosition } from "../../utils/enums";
import type { Bot } from "./botInitialState";
import {
  computeSingleBotProfit,
  computeTotalProfit,
  getProfit,
} from "./profits";

const makeBot = ({
  id,
  pair,
  fiatOrderSize,
  openingPrice,
  currentPrice,
}: {
  id: string;
  pair: string;
  fiatOrderSize: number;
  openingPrice: number;
  currentPrice: number;
}): Bot =>
  ({
    id,
    pair,
    fiat: "USDC",
    quote_asset: "USDC",
    fiat_order_size: fiatOrderSize,
    position: BotPosition.LONG,
    deal: {
      base_order_size: fiatOrderSize,
      opening_price: openingPrice,
      current_price: currentPrice,
      closing_price: 0,
    },
  }) as Bot;

describe("bot PnL helpers", () => {
  it("weights price return by fiat order size", () => {
    expect(getProfit(100, 120, BotPosition.LONG, 10)).toBe(2);
    expect(getProfit(100, 101, BotPosition.LONG, 10_000)).toBe(100);
  });

  it("computes single and total bot PnL in fiat terms", () => {
    const smallHighReturn = makeBot({
      id: "small-high-return",
      pair: "SMALLUSDC",
      fiatOrderSize: 10,
      openingPrice: 100,
      currentPrice: 120,
    });
    const largeLowReturn = makeBot({
      id: "large-low-return",
      pair: "LARGEUSDC",
      fiatOrderSize: 10_000,
      openingPrice: 100,
      currentPrice: 101,
    });

    expect(computeSingleBotProfit(smallHighReturn)).toBe(2);
    expect(computeSingleBotProfit(largeLowReturn)).toBe(100);
    expect(computeTotalProfit([smallHighReturn, largeLowReturn])).toBe(102);
  });
});
