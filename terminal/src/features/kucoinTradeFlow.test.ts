import {
  accumulateTradeFlow,
  buildTradeFlowSeries,
  parseKucoinExecution,
  pruneTradeFlowHistory,
  TRADE_FLOW_WINDOW_MS,
  type AggressiveTrade,
} from "./kucoinTradeFlow";

const now = 1_790_000_040_000;
const empty = { buckets: [], seen: {} };
const trade: AggressiveTrade = {
  id: "buy-1",
  timestamp: now,
  side: "buy",
  notional: 100,
};

describe("KuCoin aggressive trade flow", () => {
  it("preserves previous observations without creating zero-volume buckets during time away", () => {
    const first = accumulateTradeFlow(empty, [trade], now, now);
    const returnedAt = now + 3 * 60_000;
    const resumed = accumulateTradeFlow(
      first,
      [{ ...trade, id: "new", timestamp: returnedAt, notional: 40 }],
      returnedAt,
      returnedAt,
    );
    expect(resumed.buckets.map(({ timestamp }) => timestamp)).toEqual([
      now,
      returnedAt,
    ]);
    expect(buildTradeFlowSeries(resumed.buckets).map(({ cvd }) => cvd)).toEqual(
      [100, 140],
    );
    expect(resumed.seen[trade.id]).toBe(now);
  });

  it("expires saved observations without filling unobserved minutes", () => {
    const first = accumulateTradeFlow(empty, [trade], now, now);
    expect(
      pruneTradeFlowHistory(first, now + TRADE_FLOW_WINDOW_MS + 60_000),
    ).toEqual(empty);
  });

  it("values execution size using price and the futures contract multiplier", () => {
    expect(
      parseKucoinExecution(
        {
          tradeId: "a",
          ts: now * 1_000_000,
          size: 20,
          price: "0.075",
          side: "sell",
        },
        10,
      ),
    ).toEqual({ id: "a", timestamp: now, side: "sell", notional: 15 });
  });

  it.each([
    {
      tradeId: "a",
      ts: now * 1_000_000,
      size: 20,
      price: "0.075",
      side: "unknown",
    },
    {
      tradeId: "a",
      ts: now * 1_000_000,
      size: -1,
      price: "0.075",
      side: "buy",
    },
    { tradeId: "a", ts: "bad", size: 20, price: "0.075", side: "buy" },
    { tradeId: "", ts: now * 1_000_000, size: 20, price: "0.075", side: "buy" },
  ])(
    "rejects malformed executions rather than guessing aggressor side",
    (raw) => {
      expect(() => parseKucoinExecution(raw, 10)).toThrow();
    },
  );

  it("excludes duplicate trade IDs within and across updates", () => {
    const first = accumulateTradeFlow(empty, [trade, trade], now, now);
    const second = accumulateTradeFlow(
      first,
      [trade, { ...trade, id: "sell-1", side: "sell", notional: 40 }],
      now,
      now,
    );
    expect(second.buckets).toEqual([{ timestamp: now, buy: 100, sell: 40 }]);
    expect(buildTradeFlowSeries(second.buckets)[0]).toMatchObject({
      delta: 60,
      cvd: 60,
    });
  });

  it("computes per-minute delta and its cumulative sum from the same executions", () => {
    const history = accumulateTradeFlow(
      empty,
      [
        trade,
        {
          ...trade,
          id: "sell",
          timestamp: now + 60_000,
          side: "sell",
          notional: 40,
        },
        { ...trade, id: "buy", timestamp: now + 120_000, notional: 70 },
      ],
      now + 120_000,
      now,
    );
    expect(
      buildTradeFlowSeries(history.buckets).map(({ delta, cvd }) => [
        delta,
        cvd,
      ]),
    ).toEqual([
      [100, 100],
      [-40, 60],
      [70, 130],
    ]);
  });

  it("records zero volume for a quiet minute on a continuously connected stream", () => {
    const history = accumulateTradeFlow(empty, [trade], now + 60_000, now);
    expect(
      buildTradeFlowSeries(history.buckets).map(({ delta, cvd }) => [
        delta,
        cvd,
      ]),
    ).toEqual([
      [100, 100],
      [0, 100],
    ]);
  });

  it("ignores executions before collection started and prunes expired history", () => {
    expect(
      accumulateTradeFlow(empty, [{ ...trade, timestamp: now - 1 }], now, now)
        .buckets[0].buy,
    ).toBe(0);
    const history = accumulateTradeFlow(empty, [trade], now, now);
    const pruned = accumulateTradeFlow(
      history,
      [],
      now + TRADE_FLOW_WINDOW_MS + 60_000,
      now,
    );
    expect(pruned.seen).toEqual({});
    expect(
      pruned.buckets.every(({ buy, sell }) => buy === 0 && sell === 0),
    ).toBe(true);
  });
});
