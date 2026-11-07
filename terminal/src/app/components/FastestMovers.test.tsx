import "@testing-library/jest-dom";
import { render, screen as rtlScreen } from "@testing-library/react";
import FastestMovers from "./FastestMovers";

describe("FastestMovers", () => {
  it("shows one-hour direction and the optional three-hour context", () => {
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
          losers: [],
        }}
      />,
    );

    expect(rtlScreen.getByText("Fastest futures movers")).toBeInTheDocument();
    expect(rtlScreen.getByText("CARVUSDTM")).toBeInTheDocument();
    expect(rtlScreen.getByText("7.3% in 1h")).toBeInTheDocument();
    expect(rtlScreen.getByText("3h: 5.4%")).toBeInTheDocument();
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
