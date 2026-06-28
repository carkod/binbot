import { matchNewRoutes } from "./validations";

describe("matchNewRoutes", () => {
  it("matches bot creation routes with and without symbols", () => {
    expect(matchNewRoutes("/bots/futures/new")).toBe(true);
    expect(matchNewRoutes("/bots/futures/new/RAVEUSDTM")).toBe(true);
    expect(matchNewRoutes("/bots/new")).toBe(true);
    expect(matchNewRoutes("/bots/new/BTCUSDT")).toBe(true);
    expect(matchNewRoutes("/paper-trading/new")).toBe(true);
    expect(matchNewRoutes("/paper-trading/new/ETHUSDT")).toBe(true);
  });

  it("does not match edit routes", () => {
    expect(matchNewRoutes("/bots/futures/edit/123")).toBe(false);
    expect(matchNewRoutes("/bots/edit/123")).toBe(false);
  });
});
