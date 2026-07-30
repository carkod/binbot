import { render, screen as rtlScreen } from "@testing-library/react";

import { MarketType } from "../../utils/enums";
import GainersLosersCard from "./GainersLosersCard";

describe("GainersLosersCard", () => {
  it("links futures symbols to the futures bot creation route", () => {
    render(
      <GainersLosersCard
        title="Futures rankings"
        market_type={MarketType.FUTURES}
        data={[
          {
            symbol: "SNXXUSDTM",
            priceChangePercent: "4.2",
          },
        ]}
      />,
    );

    expect(
      rtlScreen.getByRole("link", { name: "SNXXUSDTM" }).getAttribute("href"),
    ).toBe("/bots/futures/new/SNXXUSDTM");
  });

  it("keeps spot symbols on the spot bot creation route", () => {
    render(
      <GainersLosersCard
        title="Spot gainers"
        data={[
          {
            symbol: "BTCUSDT",
            priceChangePercent: "2.1",
          },
        ]}
      />,
    );

    expect(
      rtlScreen.getByRole("link", { name: "BTCUSDT" }).getAttribute("href"),
    ).toBe("/bots/new/BTCUSDT");
  });
});
