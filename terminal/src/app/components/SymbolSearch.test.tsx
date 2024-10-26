import { describe, expect, it } from "vitest";
import { filterSymbolByBaseAsset } from "./SymbolSearch";

describe("Search symbols", () => {
  it("returns symbols only with the given baseAsset", () => {
    const baseAsset = "USDC";
    const listSymbols = ["USDCBNB", "BTCUSDT", "BTCUSDC", "BTCETH", "ETHUSDT", "ETHUSDC"];
    const symbols = filterSymbolByBaseAsset(listSymbols, baseAsset);

    // access Date.now() will result in the date set above
    expect(symbols).toEqual(["BTCUSDC", "ETHUSDC"]);
  });
});
