import "@testing-library/jest-dom";
import {
  render,
  screen as testingScreen,
  fireEvent,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {
  MemoryRouter,
  Route,
  Routes,
  useLocation,
  useNavigate,
} from "react-router";
import { vi } from "vitest";
import { useFuturesLiquidityQuery } from "../../../features/kucoinApiSlice";
import { SymbolContext } from "../../hooks";
import MicrostructurePage from "../Microstructure";

vi.mock("../../hooks/useKucoinTradeFlow", () => ({
  useKucoinTradeFlow: vi.fn(() => ({
    history: { buckets: [], seen: {} },
    status: "connecting",
    restarted: false,
  })),
}));

vi.mock("../../../features/kucoinApiSlice", () => ({
  useFuturesLiquidityQuery: vi.fn(),
}));

vi.mock("../../components/PlotlyChart", () => ({
  default: ({ data }: { data: { name: string }[] }) => (
    <div
      data-testid={data[0].name === "OBI" ? "obi-chart" : "spread-depth-chart"}
    >
      {JSON.stringify(data)}
    </div>
  ),
}));

const LocationControls = () => {
  const { pathname } = useLocation();
  const navigate = useNavigate();
  return (
    <>
      <output data-testid="pathname">{pathname}</output>
      <button onClick={() => navigate("/microstructure/XBTUSDTM")}>
        Change route
      </button>
    </>
  );
};

const renderPage = (path = "/microstructure") =>
  render(
    <SymbolContext.Provider
      value={{
        symbolsList: ["BTCUSDT", "KGENUSDTM", "XBTUSDTM"],
        quoteAsset: "USDT",
        baseAsset: "KGEN",
        futuresLeverage: 1,
        updateQuoteBaseState: vi.fn(),
        isLoading: false,
      }}
    >
      <MemoryRouter initialEntries={[path]}>
        <LocationControls />
        <Routes>
          <Route
            path="/microstructure/:symbol?"
            element={<MicrostructurePage />}
          />
        </Routes>
      </MemoryRouter>
    </SymbolContext.Provider>,
  );

describe("Microstructure page", () => {
  beforeEach(() => {
    vi.mocked(useFuturesLiquidityQuery).mockReturnValue({
      currentData: {
        spreadRatio: 0.0008,
        bidDepth: 30_000,
        askDepth: 20_000,
        liquidity: "High liquidity",
        obi: 0.2,
        timestamp: Date.now(),
        multiplier: 1,
      },
      isFetching: false,
      isError: false,
      refetch: vi.fn(),
    } as ReturnType<typeof useFuturesLiquidityQuery>);
  });

  it("requires a large symbol search and skips queries when no symbol is provided", () => {
    renderPage();
    expect(testingScreen.getByRole("combobox")).toBeRequired();
    expect(testingScreen.getByRole("combobox")).toHaveClass("form-control-lg");
    expect(testingScreen.getAllByText("Enter a symbol")).toHaveLength(3);
    expect(useFuturesLiquidityQuery).toHaveBeenLastCalledWith(
      "",
      expect.objectContaining({ skip: true }),
    );
  });

  it("prefills a route symbol and renders only the current liquidity label", () => {
    renderPage("/microstructure/KGENUSDTM");
    expect(testingScreen.getByRole("combobox")).toHaveValue("KGENUSDTM");
    expect(testingScreen.getByText("High liquidity")).toBeInTheDocument();
    expect(testingScreen.getByTestId("obi-chart")).toBeInTheDocument();
    expect(testingScreen.queryByText("Volume Delta")).not.toBeInTheDocument();
    const obiCard = testingScreen
      .getByText("Order Book Imbalance (OBI)")
      .closest(".card");
    const cvdCard = testingScreen
      .getByText("Cumulative Volume Delta")
      .closest(".card");
    expect(obiCard.parentElement).toHaveClass("col-md-6");
    expect(cvdCard.parentElement).toHaveClass("col-md-6");
    expect(obiCard.parentElement.parentElement).toBe(
      cvdCard.parentElement.parentElement,
    );
    expect(
      testingScreen.getByText("Spread and Nearby Depth").closest(".row"),
    ).not.toBe(obiCard.parentElement.parentElement);
    expect(testingScreen.getByTestId("spread-depth-chart")).toBeInTheDocument();
    expect(testingScreen.queryByText(/^Liquidity$/)).not.toBeInTheDocument();
    expect(useFuturesLiquidityQuery).toHaveBeenLastCalledWith(
      "KGENUSDTM",
      expect.objectContaining({ skip: false, pollingInterval: 15_000 }),
    );
  });

  it("accepts a typed symbol absent from suggestions and updates the route", async () => {
    renderPage();
    const user = userEvent.setup();
    await user.type(testingScreen.getByRole("combobox"), "newusdtm");
    expect(testingScreen.getByRole("combobox")).toHaveValue("newusdtm");
    await user.click(testingScreen.getByRole("button", { name: "Search" }));
    expect(testingScreen.getByTestId("pathname")).toHaveTextContent(
      "/microstructure/NEWUSDTM",
    );
    expect(testingScreen.getByRole("combobox")).toHaveValue("NEWUSDTM");
  });

  it("selects a suggestion without needing to blur the search", async () => {
    renderPage();
    const user = userEvent.setup();
    await user.type(testingScreen.getByRole("combobox"), "KGEN");
    await user.click(testingScreen.getByRole("option", { name: "KGENUSDTM" }));
    expect(testingScreen.getByTestId("pathname")).toHaveTextContent(
      "/microstructure/KGENUSDTM",
    );
  });

  it("hides the previous symbol's label while changing or clearing the search", () => {
    renderPage("/microstructure/KGENUSDTM");
    fireEvent.change(testingScreen.getByRole("combobox"), {
      target: { value: "XBT" },
    });
    expect(testingScreen.queryByText("High liquidity")).not.toBeInTheDocument();
    fireEvent.change(testingScreen.getByRole("combobox"), {
      target: { value: "" },
    });
    expect(testingScreen.getByRole("combobox")).toHaveValue("");
    expect(testingScreen.getAllByText("Enter a symbol")).toHaveLength(3);
  });

  it("syncs the search with route changes", async () => {
    renderPage("/microstructure/KGENUSDTM");
    await userEvent.click(
      testingScreen.getByRole("button", { name: "Change route" }),
    );
    expect(testingScreen.getByRole("combobox")).toHaveValue("XBTUSDTM");
    expect(useFuturesLiquidityQuery).toHaveBeenLastCalledWith(
      "XBTUSDTM",
      expect.objectContaining({ skip: false }),
    );
  });

  it("submits symbols without checking their format and lets KuCoin validate them", async () => {
    renderPage();
    const user = userEvent.setup();
    await user.type(testingScreen.getByRole("combobox"), "BTCUSDT");
    await user.click(testingScreen.getByRole("button", { name: "Search" }));
    expect(testingScreen.getByTestId("pathname")).toHaveTextContent(
      "/microstructure/BTCUSDT",
    );
    expect(useFuturesLiquidityQuery).toHaveBeenLastCalledWith(
      "BTCUSDT",
      expect.objectContaining({ skip: false }),
    );
  });

  it("queries an arbitrary route symbol and shows the KuCoin 40X message", () => {
    vi.mocked(useFuturesLiquidityQuery).mockReturnValue({
      currentData: undefined,
      isFetching: false,
      isError: true,
      error: { status: 400, data: { code: "400100", msg: "Symbol not found" } },
      refetch: vi.fn(),
    } as ReturnType<typeof useFuturesLiquidityQuery>);
    renderPage("/microstructure/UNKNOWN");
    expect(useFuturesLiquidityQuery).toHaveBeenLastCalledWith(
      "UNKNOWN",
      expect.objectContaining({ skip: false }),
    );
    expect(testingScreen.getByRole("alert")).toHaveTextContent(
      "Symbol not found",
    );
    expect(testingScreen.getByRole("combobox")).toHaveClass("is-invalid");
    fireEvent.change(testingScreen.getByRole("combobox"), {
      target: { value: "XBT" },
    });
    expect(testingScreen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("shows unavailable and allows retry when a refresh fails, even with cached data", async () => {
    const refetch = vi.fn();
    vi.mocked(useFuturesLiquidityQuery).mockReturnValue({
      currentData: {
        spreadRatio: 0.0008,
        bidDepth: 30_000,
        askDepth: 20_000,
        liquidity: "High liquidity",
        obi: 0.2,
        timestamp: Date.now(),
        multiplier: 1,
      },
      isFetching: false,
      isError: true,
      refetch,
    } as ReturnType<typeof useFuturesLiquidityQuery>);
    renderPage("/microstructure/KGENUSDTM");
    expect(
      testingScreen.getByText(/Liquidity unavailable/),
    ).toBeInTheDocument();
    expect(testingScreen.queryByText("High liquidity")).not.toBeInTheDocument();
    expect(
      testingScreen.getByText(/Spread and depth unavailable/),
    ).toBeInTheDocument();
    await userEvent.click(
      testingScreen.getAllByRole("button", { name: "Retry" })[0],
    );
    expect(refetch).toHaveBeenCalledOnce();
  });
});
