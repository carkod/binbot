import "@testing-library/jest-dom";
import {
  fireEvent,
  render,
  screen as testingScreen,
} from "@testing-library/react";
import { vi } from "vitest";
import { singleBot } from "../../../features/bots/botInitialState";
import { setCurrentPrice } from "../../../features/bots/botSlice";
import { BotStatus, MarketType } from "../../../utils/enums";
import { useGetSettingsQuery } from "../../../features/autotradeApiSlice";
import { useMicrostructureData } from "../../hooks/useMicrostructureData";
import BotChartTabs from "../BotChartTabs";
import { useCvdSymbolQuery } from "../../../features/marketApiSlice";

vi.mock("../../../features/autotradeApiSlice", () => ({
  useGetSettingsQuery: vi.fn(),
}));
vi.mock("../../hooks/useMicrostructureData", () => ({
  useMicrostructureData: vi.fn(),
}));
vi.mock("../ChartContainer", () => ({
  default: () => <input aria-label="Chart state" defaultValue="original" />,
}));
vi.mock("../SpreadAndDepthCard", () => ({
  default: () => <div>Shared order book charts</div>,
}));
vi.mock("../LivePlotlyChart", () => ({
  default: () => <div>Stored CVD chart</div>,
}));
vi.mock("../../../features/marketApiSlice", () => ({
  useCvdSymbolQuery: vi.fn(() => ({ isFetching: false, isError: false })),
}));

const bot = {
  ...singleBot,
  id: "futures-bot",
  pair: "PROMUSDTM",
  market_type: MarketType.FUTURES,
  status: BotStatus.ACTIVE,
  fiat_order_size: 100,
  deal: { ...singleBot.deal, opening_price: 100, current_price: 110 },
};
const selectSymbol = vi.fn();
const props = { bot, setCurrentPrice, marketType: MarketType.FUTURES };

describe("bot chart tabs", () => {
  beforeEach(() => {
    vi.mocked(useGetSettingsQuery).mockReturnValue({
      data: { exchange_id: "kucoin" },
      refetch: vi.fn(),
    } as ReturnType<typeof useGetSettingsQuery>);
    vi.mocked(useMicrostructureData).mockReturnValue({
      symbol: bot.pair,
      selectSymbol,
      orderBookHistory: { history: [], chartPoints: [], now: Date.now() },
      liquidity: {
        refetch: vi.fn(),
        isFetching: false,
        isError: false,
      } as ReturnType<typeof useMicrostructureData>["liquidity"],
    });
  });

  it("keeps the bot heading above the tabs and updates profit from current bot prices", () => {
    const { rerender } = render(<BotChartTabs {...props} />);
    const heading = testingScreen.getByRole("heading", { level: 3 });
    expect(heading).toHaveTextContent("PROMUSDTM 10% active long Futures");
    expect(heading.closest(".card").nextElementSibling).toContainElement(
      testingScreen.getByRole("tablist"),
    );
    rerender(
      <BotChartTabs
        {...props}
        bot={{ ...bot, deal: { ...bot.deal, current_price: 90 } }}
      />,
    );
    expect(testingScreen.getByText("-10%")).toHaveClass("bg-danger");
  });

  it("selects the bot symbol and preserves price chart state across tab changes", () => {
    render(<BotChartTabs {...props} />);
    expect(selectSymbol).toHaveBeenCalledWith("PROMUSDTM");
    const chart = testingScreen.getByRole("textbox", { name: "Chart state" });
    fireEvent.change(chart, { target: { value: "zoomed" } });
    fireEvent.click(
      testingScreen.getByRole("tab", { name: "Order book analysis" }),
    );
    expect(
      testingScreen.getByText("Shared order book charts"),
    ).toBeInTheDocument();
    expect(useCvdSymbolQuery).toHaveBeenLastCalledWith(
      "PROMUSDTM",
      expect.objectContaining({ skip: false, pollingInterval: 30_000 }),
    );
    fireEvent.click(testingScreen.getByRole("tab", { name: "Chart" }));
    expect(testingScreen.getByRole("textbox", { name: "Chart state" })).toBe(
      chart,
    );
    expect(chart).toHaveValue("zoomed");
  });

  it("requests stored CVD for the changed futures symbol even when its order book fails", () => {
    const { rerender } = render(<BotChartTabs {...props} />);
    const context = vi.mocked(useMicrostructureData).mock.results[0].value;
    vi.mocked(useMicrostructureData).mockReturnValue({
      ...context,
      symbol: "XBTUSDTM",
      liquidity: { ...context.liquidity, isError: true },
    });
    rerender(<BotChartTabs {...props} bot={{ ...bot, pair: "XBTUSDTM" }} />);
    fireEvent.click(
      testingScreen.getByRole("tab", { name: "Order book analysis" }),
    );
    expect(useCvdSymbolQuery).toHaveBeenLastCalledWith(
      "XBTUSDTM",
      expect.objectContaining({ skip: false }),
    );
    expect(
      testingScreen.getByText(/no observations yet for XBTUSDTM/),
    ).toBeInTheDocument();
  });

  it("selects a changed symbol and waits for its collector before showing analysis", () => {
    const { rerender } = render(<BotChartTabs {...props} />);
    rerender(<BotChartTabs {...props} bot={{ ...bot, pair: "XBTUSDTM" }} />);
    expect(selectSymbol).toHaveBeenLastCalledWith("XBTUSDTM");
    fireEvent.click(
      testingScreen.getByRole("tab", { name: "Order book analysis" }),
    );
    expect(testingScreen.getByRole("status")).toHaveTextContent(
      "Starting order book analysis",
    );
  });

  it("explains supported markets for spot bots without selecting a futures collector", () => {
    render(<BotChartTabs {...props} marketType={MarketType.SPOT} />);
    expect(selectSymbol).not.toHaveBeenCalled();
    fireEvent.click(
      testingScreen.getByRole("tab", { name: "Order book analysis" }),
    );
    expect(
      testingScreen.getByText(/available for KuCoin futures bots/),
    ).toBeInTheDocument();
  });
});
