import { summarizeRecentTrades, type KucoinMarketTrade } from "./kucoinTrades";

const NOW = 1_000_000;

const trade = (
  overrides: Partial<KucoinMarketTrade> = {},
): KucoinMarketTrade => ({
  tradeId: "1",
  side: "buy",
  price: 100,
  size: 10,
  timestamp: NOW - 1_000,
  ...overrides,
});

describe("recent market trades", () => {
  it("values trades as price x contracts x multiplier", () => {
    const { trades, buy } = summarizeRecentTrades([trade()], 0.1, NOW);

    expect(trades[0].notional).toBeCloseTo(100);
    expect(buy).toBeCloseTo(100);
  });

  it("keeps only the last 5 minutes of trades", () => {
    const { trades } = summarizeRecentTrades(
      [
        trade({ tradeId: "old", timestamp: NOW - 300_001 }),
        trade({ tradeId: "edge", timestamp: NOW - 300_000 }),
        trade({ tradeId: "future", timestamp: NOW + 1 }),
      ],
      1,
      NOW,
    );

    expect(trades.map(({ tradeId }) => tradeId)).toEqual(["edge"]);
  });

  it("reports aggressive buy minus sell as the delta, oldest trade first", () => {
    const summary = summarizeRecentTrades(
      [
        trade({ tradeId: "sell", side: "sell", size: 4, timestamp: NOW - 500 }),
        trade({ tradeId: "buy", side: "buy", size: 10, timestamp: NOW - 900 }),
      ],
      1,
      NOW,
    );

    expect(summary.buy).toBe(1000);
    expect(summary.sell).toBe(400);
    expect(summary.delta).toBe(600);
    expect(summary.trades.map(({ tradeId }) => tradeId)).toEqual([
      "buy",
      "sell",
    ]);
  });
});
