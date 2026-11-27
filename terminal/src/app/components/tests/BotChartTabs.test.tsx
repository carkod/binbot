import "@testing-library/jest-dom";
import { vi } from "vitest";
import { useGetSettingsQuery } from "../../../features/autotradeApiSlice";
import { singleBot } from "../../../features/bots/botInitialState";
import { setCurrentPrice } from "../../../features/bots/botSlice";
import { useCvdSymbolQuery } from "../../../features/marketApiSlice";
import { BotStatus, MarketType } from "../../../utils/enums";
import {
  fireEvent,
  render,
  screen as testingScreen,
} from "../../../utils/render";
import { useMicrostructureData } from "../../hooks/useMicrostructureData";
import BotChartTabs from "../BotChartTabs";

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
vi.mock("../SymbolTradesCard", () => ({
  default: () => <div>Market trades card</div>,
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

    const heading = testingScreen.getByRole("heading", { level: 2 });

    expect(heading).toHaveTextContent("PROMUSDTM 10% active long Futures");
    expect(heading.nextElementSibling).toContainElement(
      testingScreen.getByRole("tablist"),
    );
    rerender(
      <BotChartTabs
        {...props}
        bot={{ ...bot, deal: { ...bot.deal, current_price: 90 } }}
      />,
    );
    expect(
      testingScreen.getByText("-10%").closest(".mantine-Badge-root"),
    ).toHaveStyle({
      "--badge-color": "var(--mantine-color-danger-light-color)",
    });
  });

  it("loads analysis before the tab opens and preserves charts across tab changes", () => {
    render(<BotChartTabs {...props} />);
    expect(selectSymbol).toHaveBeenCalledWith("PROMUSDTM");
    expect(useCvdSymbolQuery).toHaveBeenCalledWith(
      "PROMUSDTM",
      expect.objectContaining({ skip: false, pollingInterval: 30_000 }),
    );

    const analysis = testingScreen.getByText("Shared order book charts");

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
    expect(testingScreen.getByText("Shared order book charts")).toBe(analysis);
    expect(testingScreen.getByRole("textbox", { name: "Chart state" })).toBe(
      chart,
    );
    expect(chart).toHaveValue("zoomed");
  });

  it("restores the analysis tab and reports changes to the page", () => {
    const onTabChange = vi.fn();

    const { rerender } = render(
      <BotChartTabs
        {...props}
        activeTab="analysis"
        onTabChange={onTabChange}
      />,
    );

    expect(
      testingScreen.getByRole("tab", { name: "Order book analysis" }),
    ).toHaveAttribute("aria-selected", "true");

    fireEvent.click(testingScreen.getByRole("tab", { name: "Chart" }));
    expect(onTabChange).toHaveBeenCalledWith("chart");
    rerender(
      <BotChartTabs {...props} activeTab="chart" onTabChange={onTabChange} />,
    );
    expect(testingScreen.getByRole("tab", { name: "Chart" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
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
