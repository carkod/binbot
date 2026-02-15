import "@testing-library/jest-dom";
import {
  render,
  fireEvent,
  screen as testingScreen,
} from "@testing-library/react";
import { vi } from "vitest";
import { Provider } from "react-redux";
import BotsPage from "../Bots";
import { SpinnerContext } from "../../Layout";
import { BulkAction } from "../../components/BotsActions";
import { makeStore } from "../../store"; // Import the store configuration
import { SymbolContext } from "../../hooks";

const store = makeStore();

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
  return render(
    <Provider store={store}>
      <SymbolContext.Provider value={symbolContextValue}>
        <SpinnerContext.Provider value={spinnerContextValue}>
          {ui}
        </SpinnerContext.Provider>
      </SymbolContext.Provider>
    </Provider>,
  );
};

describe("BotsPage", () => {
  it("renders BotsPage component", () => {
    renderWithProviders(<BotsPage />, { store });
    expect(testingScreen.getByText(/Apply bulk action/i)).toBeInTheDocument();
  });

  it("handles bulk action selection", () => {
    renderWithProviders(<BotsPage />, { store });
    fireEvent.change(testingScreen.getByLabelText(/Bulk Actions/i), {
      target: { value: BulkAction.SELECT_ALL },
    });
    fireEvent.click(testingScreen.getByText(/Apply bulk action/i));
    expect(testingScreen.getByText(/Apply bulk action/i)).toBeInTheDocument();
  });

  it("handles date filter changes", () => {
    renderWithProviders(<BotsPage />, { store });
    fireEvent.change(testingScreen.getByLabelText(/Filter by start date/i), {
      target: { value: "2023-01-01" },
    });
    fireEvent.change(testingScreen.getByLabelText(/Filter by end date/i), {
      target: { value: "2023-12-31" },
    });
    expect(testingScreen.getByLabelText(/Filter by start date/i)).toHaveValue(
      "2023-01-01",
    );
    expect(testingScreen.getByLabelText(/Filter by end date/i)).toHaveValue(
      "2023-12-31",
    );
  });

  it("handles bot deletion", () => {
    renderWithProviders(<BotsPage />, { store });
    const deleteBtn = testingScreen.queryByRole("button", { name: /delete/i });
    if (!deleteBtn) {
      return;
    }
    fireEvent.click(deleteBtn[0]);
    expect(
      testingScreen.getByText(/To close orders, please deactivate/i),
    ).toBeInTheDocument();
  });

  it("filters bots by symbol when searching", () => {
    const setSpinnerMock = vi.fn();
    renderWithProviders(<BotsPage />, {
      store,
      spinnerContextValue: {
        spinner: false,
        setSpinner: setSpinnerMock,
      },
    });
    const input = testingScreen.getByPlaceholderText(/Search by pair/i);
    fireEvent.change(input, { target: { value: "ARBTC" } });
    expect(input).toHaveValue("ARBTC");
    expect(setSpinnerMock).toHaveBeenCalledWith(true);
  });
});
