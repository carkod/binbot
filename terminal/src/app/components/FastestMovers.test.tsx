import "@testing-library/jest-dom";
import { render, screen as rtlScreen } from "@testing-library/react";
import FastestMovers from "./FastestMovers";

describe("FastestMovers", () => {
  it("links futures movers to new bots and shows both time windows as badges", () => {
    render(
      <FastestMovers
        data={{
          source: "kucoin_futures",
          recorded_at: "2026-11-07T00:00:00Z",
          comparison_at: "2026-11-06T23:00:00Z",
          gainers: [
            {
              symbol: "CARVUSDTM",
              price_change_1h_percent: 7.3,
              price_change_3h_percent: 5.4,
              price_change_percent: 13.8,
              last_price: 0.03335,
              turnover_24h: 38_563,
            },
          ],
          losers: [
            {
              symbol: "KOMAUSDTM",
              price_change_1h_percent: -4.2,
              price_change_3h_percent: -6.1,
              price_change_percent: -9.8,
              last_price: 0.012,
              turnover_24h: 42_000,
            },
          ],
        }}
      />,
    );

    expect(rtlScreen.getByText("Fastest futures movers")).toBeInTheDocument();
    expect(
      rtlScreen.getByText(
        "When gainers dominate losers, look at Rising. When losers dominate gainers, look at Falling.",
      ),
    ).toHaveClass("alert-warning", "alert-subtle");
    expect(rtlScreen.getByText("Rising")).toBeInTheDocument();
    expect(rtlScreen.getByText("Falling")).toBeInTheDocument();
    expect(
      rtlScreen.getByRole("link", { name: "CARVUSDTM" }).getAttribute("href"),
    ).toBe("/bots/futures/new/CARVUSDTM");
    expect(
      rtlScreen.getByRole("link", { name: "KOMAUSDTM" }).getAttribute("href"),
    ).toBe("/bots/futures/new/KOMAUSDTM");
    expect(rtlScreen.getByText("7.3% in 1h")).toBeInTheDocument();
    expect(rtlScreen.getByText("5.4% in 3h")).toHaveClass("bg-success");
    expect(rtlScreen.getByText("-6.1% in 3h")).toHaveClass("bg-danger");
  });

  it("shows the collection state before two snapshots exist", () => {
    render(<FastestMovers data={undefined} />);

    expect(
      rtlScreen.getByText(
        "Waiting for futures price snapshots one hour apart.",
      ),
    ).toBeInTheDocument();
  });
});
