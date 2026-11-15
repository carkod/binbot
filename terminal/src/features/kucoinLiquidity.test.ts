import {
  analyzeKucoinOrderBook,
  updateObiHistory,
  OBI_WINDOW_MS,
  type ObiSnapshot,
  type KucoinOrderBook,
} from "./kucoinLiquidity";

const deepBook: KucoinOrderBook = {
  symbol: "KGENUSDTM",
  ts: 1_790_000_000_000_000_000,
  bids: [[99.96, 200]],
  asks: [[100.04, 200]],
};

describe("KuCoin futures liquidity", () => {
  it("reports midpoint-relative spread and nearby notional depth using the multiplier", () => {
    const result = analyzeKucoinOrderBook(
      {
        ...deepBook,
        bids: [
          [99.96, 200],
          [99.8, 100],
          [90, 100_000],
        ],
        asks: [
          [100.04, 200],
          [100.2, 50],
          [110, 100_000],
        ],
      },
      0.001,
    );
    expect(result.spreadRatio).toBeCloseTo(0.0008);
    expect(result.bidDepth).toBeCloseTo(29.972);
    expect(result.askDepth).toBeCloseTo(25.018);
  });

  it("calculates balanced depth as zero OBI", () => {
    expect(
      analyzeKucoinOrderBook(
        { ...deepBook, bids: [[100, 100.08]], asks: [[100.08, 100]] },
        1,
      ).obi,
    ).toBeCloseTo(0);
  });

  it("calculates bid dominance and ask dominance symmetrically", () => {
    expect(
      analyzeKucoinOrderBook(
        { ...deepBook, bids: [[100, 300.24]], asks: [[100.08, 100]] },
        1,
      ).obi,
    ).toBeCloseTo(0.5);
    expect(
      analyzeKucoinOrderBook(
        { ...deepBook, bids: [[100, 100.08]], asks: [[100.08, 300]] },
        1,
      ).obi,
    ).toBeCloseTo(-0.5);
  });

  it("uses only nearby depth for OBI and returns null when the band is empty", () => {
    expect(
      analyzeKucoinOrderBook(
        { ...deepBook, bids: [[90, 100_000]], asks: [[110, 100_000]] },
        1,
      ).obi,
    ).toBeNull();
    expect(
      analyzeKucoinOrderBook(
        {
          ...deepBook,
          bids: [
            [99.96, 1],
            [90, 100_000],
          ],
          asks: [[100.04, 200]],
        },
        1,
      ).obi,
    ).toBe(analyzeKucoinOrderBook({ ...deepBook, bids: [[99.96, 1]] }, 1).obi);
  });
  it("labels a tight spread with depth on both sides as high liquidity", () => {
    expect(analyzeKucoinOrderBook(deepBook, 1).liquidity).toBe(
      "High liquidity",
    );
  });

  it("uses contract multiplier to value depth rather than contract count", () => {
    expect(analyzeKucoinOrderBook(deepBook, 0.001).liquidity).toBe(
      "Low liquidity",
    );
    expect(analyzeKucoinOrderBook(deepBook, 10).liquidity).toBe(
      "High liquidity",
    );
  });

  it("requires depth on each side even when the opposite side is deep", () => {
    expect(
      analyzeKucoinOrderBook({ ...deepBook, asks: [[100.04, 1]] }, 1).liquidity,
    ).toBe("Low liquidity");
  });

  it("labels a wide spread as low liquidity even with deep orders", () => {
    expect(
      analyzeKucoinOrderBook({ ...deepBook, asks: [[100.2, 200]] }, 1)
        .liquidity,
    ).toBe("Low liquidity");
  });

  it("ignores large orders outside the near-price band", () => {
    expect(
      analyzeKucoinOrderBook(
        {
          ...deepBook,
          bids: [
            [99.96, 1],
            [90, 100_000],
          ],
          asks: [
            [100.04, 1],
            [110, 100_000],
          ],
        },
        1,
      ).liquidity,
    ).toBe("Low liquidity");
  });

  it("sums nearby levels and handles string values and unordered levels", () => {
    expect(
      analyzeKucoinOrderBook(
        {
          ...deepBook,
          bids: [
            ["99.8", "60"],
            ["99.96", "60"],
          ],
          asks: [
            ["100.2", "60"],
            ["100.04", "60"],
          ],
        },
        1,
      ).liquidity,
    ).toBe("High liquidity");
  });

  it.each([0, -1, NaN, Infinity])(
    "rejects an invalid multiplier %s",
    (multiplier) => {
      expect(() => analyzeKucoinOrderBook(deepBook, multiplier)).toThrow();
    },
  );

  it.each([
    { ...deepBook, bids: [] },
    { ...deepBook, bids: [["bad", 200]] },
    { ...deepBook, bids: [[99.96, -1]] },
    { ...deepBook, bids: [[101, 200]] },
    { ...deepBook, asks: [[99.96, 200]] },
  ])(
    "rejects missing, invalid, or crossed books instead of labeling them",
    (book) => {
      expect(() =>
        analyzeKucoinOrderBook(book as KucoinOrderBook, 1),
      ).toThrow();
    },
  );
});

describe("rolling OBI history", () => {
  const now = 1_790_000_000_000;
  const point: ObiSnapshot = {
    spreadRatio: 0.0008,
    bidDepth: 30_000,
    askDepth: 20_000,
    multiplier: 1,
    liquidity: "High liquidity",
    obi: 0.2,
    timestamp: now,
  };

  it("retains only samples inside the preceding 15 minutes", () => {
    const old = { ...point, timestamp: now - OBI_WINDOW_MS - 1 };
    const boundary = { ...point, timestamp: now - OBI_WINDOW_MS };
    expect(updateObiHistory([old, boundary], point, now)).toEqual([
      boundary,
      point,
    ]);
  });

  it("does not duplicate the same exchange snapshot", () => {
    expect(updateObiHistory([point], { ...point }, now)).toEqual([point]);
  });

  it("expires data even without a successful new response", () => {
    expect(
      updateObiHistory([point], undefined, now + OBI_WINDOW_MS + 1),
    ).toEqual([]);
  });

  it("rejects expired or invalid new samples and sorts out-of-order snapshots", () => {
    expect(updateObiHistory([], { ...point, timestamp: NaN }, now)).toEqual([]);
    expect(
      updateObiHistory(
        [],
        { ...point, timestamp: now - OBI_WINDOW_MS - 1 },
        now,
      ),
    ).toEqual([]);
    const earlier = { ...point, timestamp: now - 15_000 };
    expect(updateObiHistory([point], earlier, now)).toEqual([earlier, point]);
  });
});
