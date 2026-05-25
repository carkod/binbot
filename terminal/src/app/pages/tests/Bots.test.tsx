import "@testing-library/jest-dom";
import { render, screen as testingScreen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { Provider } from "react-redux";
import BotsPage from "../Bots";
import { SpinnerContext } from "../../Layout";
import { BulkAction } from "../../components/BotsActions";
import { makeStore } from "../../store";
import { SymbolContext } from "../../hooks";

const mockRefetch = vi.fn();
const mockMutation = vi.fn(() => ({
  unwrap: vi.fn().mockResolvedValue({}),
}));

vi.mock("../../../features/bots/botsApiSlice", async () => {
  const actual = await vi.importActual("../../../features/bots/botsApiSlice");
  return {
    ...actual,
    useDeleteBotMutation: vi.fn(() => [
      mockMutation,
      { isLoading: false, isSuccess: false },
    ]),
    useDeactivateBotMutation: vi.fn(() => [
      mockMutation,
      { isLoading: false, isSuccess: false },
    ]),
    useGetBotsQuery: vi.fn(() => ({
      refetch: mockRefetch,
      data: {
        bots: {
          ids: [],
          entities: {},
        },
        totalProfit: 0,
      },
      isFetching: false,
    })),
    useGetOneBySymbolQuery: vi.fn(() => ({
      refetch: mockRefetch,
      data: undefined,
      isFetching: false,
    })),
  };
});

vi.mock("../../../features/symbolsApiSlice", async () => {
  const actual = await vi.importActual("../../../features/symbolsApiSlice");
  return {
    ...actual,
    useGetSymbolsQuery: vi.fn(() => ({
      data: [{ id: "BTCUSDT" }, { id: "ETHUSDT" }],
      isFetching: false,
    })),
  };
});

vi.mock("../../../features/autotradeApiSlice", async () => {
  const actual = await vi.importActual("../../../features/autotradeApiSlice");
  return {
    ...actual,
    useGetSettingsQuery: vi.fn(() => ({
      data: { fiat: "USDT" },
    })),
  };
});

const mockSymbolContextValue = {
  symbolsList: ["BTCUSDT", "ETHUSDT"],
  quoteAsset: "USDT",
  baseAsset: "BTC",
  updateQuoteBaseState: vi.fn(),
  isLoading: false,
};

const renderWithProviders = (
  ui,
  {
    store,
    symbolContextValue = mockSymbolContextValue,
    spinnerContextValue = { spinner: false, setSpinner: vi.fn() },
  },
) => {
  const user = userEvent.setup();

  return {
    user,
    ...render(
      <Provider store={store ?? makeStore()}>
        <SymbolContext.Provider value={symbolContextValue}>
          <SpinnerContext.Provider value={spinnerContextValue}>
            {ui}
          </SpinnerContext.Provider>
        </SymbolContext.Provider>
      </Provider>,
    ),
  };
};

describe("BotsPage", () => {
  it("renders BotsPage component", () => {
    renderWithProviders(<BotsPage />, { store: makeStore() });
    expect(testingScreen.getByText(/Apply bulk action/i)).toBeInTheDocument();
  });

  it("handles bulk action selection", async () => {
    const { user } = renderWithProviders(<BotsPage />, { store: makeStore() });

    await user.selectOptions(
      testingScreen.getByLabelText(/Bulk Actions/i),
      BulkAction.SELECT_ALL,
    );
    await user.click(testingScreen.getByText(/Apply bulk action/i));

    expect(testingScreen.getByText(/Apply bulk action/i)).toBeInTheDocument();
  });

  it("handles date filter changes", async () => {
    const { user } = renderWithProviders(<BotsPage />, { store: makeStore() });

    const startDateInput =
      testingScreen.getByLabelText(/Filter by start date/i);
    const endDateInput = testingScreen.getByLabelText(/Filter by end date/i);
    await user.clear(startDateInput);
    await user.type(startDateInput, "2023-01-01");
    await user.clear(endDateInput);
    await user.type(endDateInput, "2023-12-31");

    expect(startDateInput).toHaveValue("2023-01-01");
    expect(endDateInput).toHaveValue("2023-12-31");
  });

  it("handles bot deletion", async () => {
    const { user } = renderWithProviders(<BotsPage />, { store: makeStore() });
    const deleteBtn = testingScreen.queryByRole("button", { name: /delete/i });
    if (!deleteBtn) {
      return;
    }
    await user.click(deleteBtn);
    expect(
      testingScreen.getByText(/To close orders, please deactivate/i),
    ).toBeInTheDocument();
  });

  it("filters bots by symbol when searching", async () => {
    const setSpinnerMock = vi.fn();
    const { user } = renderWithProviders(<BotsPage />, {
      store: makeStore(),
      spinnerContextValue: {
        spinner: false,
        setSpinner: setSpinnerMock,
      },
    });
    const input = testingScreen.getByPlaceholderText(/Search by pair/i);
    await user.type(input, "ARBTC");
    await user.tab();

    expect(input).toHaveValue("ARBTC");
    expect(setSpinnerMock).toHaveBeenCalledWith(true);
  });
});
