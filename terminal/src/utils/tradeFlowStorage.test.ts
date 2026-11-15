import { IDBFactory as FakeIDBFactory } from "fake-indexeddb";
import { vi } from "vitest";
import { loadTradeFlowHistory, saveTradeFlowHistory } from "./tradeFlowStorage";

const savedHistory = {
  buckets: [
    { timestamp: 1_790_000_040_000, buy: 15, sell: 5, gapBefore: true },
  ],
  seen: { trade: 1_790_000_040_000 },
};

describe("IndexedDB trade history", () => {
  beforeEach(() => vi.stubGlobal("indexedDB", new FakeIDBFactory()));
  afterEach(() => vi.unstubAllGlobals());

  it("restores buckets, coverage flags and deduplication IDs after reopening the database", async () => {
    await saveTradeFlowHistory("KGENUSDTM", 10, savedHistory);
    expect(await loadTradeFlowHistory("KGENUSDTM", 10)).toEqual(savedHistory);
  });

  it("isolates symbols and replaces snapshots without appending duplicate buckets", async () => {
    await saveTradeFlowHistory("KGENUSDTM", 10, savedHistory);
    const other = {
      buckets: [{ timestamp: 1_790_000_040_000, buy: 42, sell: 0 }],
      seen: {},
    };
    await saveTradeFlowHistory("XBTUSDTM", 0.001, other);
    await saveTradeFlowHistory("KGENUSDTM", 10, savedHistory);
    expect(await loadTradeFlowHistory("KGENUSDTM", 10)).toEqual(savedHistory);
    expect(await loadTradeFlowHistory("XBTUSDTM", 0.001)).toEqual(other);
    expect(await loadTradeFlowHistory("NEWUSDTM", 1)).toEqual({
      buckets: [],
      seen: {},
    });
  });

  it("does not restore values calculated using a different contract multiplier", async () => {
    await saveTradeFlowHistory("KGENUSDTM", 10, savedHistory);
    expect(await loadTradeFlowHistory("KGENUSDTM", 1)).toEqual({
      buckets: [],
      seen: {},
    });
  });

  it("reports unavailable storage to the caller", async () => {
    vi.stubGlobal("indexedDB", undefined);
    await expect(loadTradeFlowHistory("KGENUSDTM", 10)).rejects.toThrow();
    await expect(
      saveTradeFlowHistory("KGENUSDTM", 10, savedHistory),
    ).rejects.toThrow();
  });
});
