import "@testing-library/jest-dom";
import type { ReactElement } from "react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { filterSymbolByBaseAsset } from "../../../utils/api";
import { fireEvent, render, screen as rtlScreen } from "../../../utils/render";
import { SymbolContext } from "../../hooks";
import SymbolSearch from "../SymbolSearch";

vi.mock("../../../features/autotradeApiSlice", () => ({
  useGetSettingsQuery: vi.fn(() => ({ data: {} })),
}));

const mockSymbolContextValue = {
  symbolsList: ["BTCUSDT", "ETHUSDT"],
  quoteAsset: "USDT",
  baseAsset: "BTC",
  futuresLeverage: 1,
  updateQuoteBaseState: vi.fn(),
  isLoading: false,
};

const renderWithSymbolProvider = (ui: ReactElement) =>
  render(
    <SymbolContext.Provider value={mockSymbolContextValue}>
      {ui}
    </SymbolContext.Provider>,
  );

const renderWithSymbols = (ui: ReactElement, symbolsList: string[]) =>
  render(
    <SymbolContext.Provider
      value={{
        ...mockSymbolContextValue,
        symbolsList,
      }}
    >
      {ui}
    </SymbolContext.Provider>,
  );

describe("Search symbols", () => {
  it("returns symbols only with the given baseAsset", () => {
    const baseAsset = "USDC";

    const listSymbols = ["USDCBNB", "BTCUSDC", "BTCETH", "ETHUSDT", "ETHUSDC"];

    const symbols = filterSymbolByBaseAsset(listSymbols, baseAsset);

    expect(symbols).toEqual(["BTCUSDC", "ETHUSDC"]);
  });
});

describe("SymbolSearch component", () => {
  it("selects a suggestion with the keyboard while keeping typing separate", async () => {
    const user = userEvent.setup();

    const onChange = vi.fn();

    const onInputChange = vi.fn();

    renderWithSymbolProvider(
      <SymbolSearch
        name="pair"
        onChange={onChange}
        onInputChange={onInputChange}
      />,
    );

    const input = rtlScreen.getByRole("combobox");

    await user.type(input, "ETH");
    expect(onInputChange).toHaveBeenLastCalledWith("ETH");
    expect(onChange).not.toHaveBeenCalled();
    await user.keyboard("{ArrowDown}{Enter}");
    expect(onChange).toHaveBeenCalledWith("ETHUSDT");
    expect(input).toHaveValue("ETHUSDT");
  });

  it("selects a suggestion with the mouse", async () => {
    const user = userEvent.setup();

    const onChange = vi.fn();

    renderWithSymbolProvider(<SymbolSearch name="pair" onChange={onChange} />);

    await user.click(rtlScreen.getByRole("combobox"));
    await user.click(await rtlScreen.findByRole("option", { name: "BTCUSDT" }));
    expect(onChange).toHaveBeenCalledWith("BTCUSDT");
  });

  it("does not render label if not passed", () => {
    renderWithSymbolProvider(
      <SymbolSearch name="pair" options={["BTCUSDT"]} />,
    );
    // Should not find any label element
    expect(rtlScreen.queryByText(/Select pair/i)).not.toBeInTheDocument();
  });

  it("renders label if passed", () => {
    renderWithSymbolProvider(
      <SymbolSearch name="pair" label="Select pair" options={["BTCUSDT"]} />,
    );
    expect(rtlScreen.getByText("Select pair")).toBeInTheDocument();
  });

  it("renders placeholder if passed", () => {
    renderWithSymbolProvider(
      <SymbolSearch
        name="pair"
        options={["BTCUSDT"]}
        placeholder="Search by pair"
      />,
    );
    expect(
      rtlScreen.getByPlaceholderText("Search by pair"),
    ).toBeInTheDocument();
  });

  it("shows error message when errors object is passed", () => {
    renderWithSymbolProvider(
      <SymbolSearch
        name="pair"
        options={["BTCUSDT"]}
        errors={{ pair: "Invalid symbol" }}
        required={true}
      />,
    );
    expect(rtlScreen.getByText("Invalid symbol")).toBeInTheDocument();
  });

  it("clears the selected symbol when value becomes empty", () => {
    const { rerender } = renderWithSymbolProvider(
      <SymbolSearch name="pair" value="RAVEUSDTM" />,
    );

    expect(rtlScreen.getByRole("combobox")).toHaveValue("RAVEUSDTM");

    rerender(
      <SymbolContext.Provider value={mockSymbolContextValue}>
        <SymbolSearch name="pair" value="" />
      </SymbolContext.Provider>,
    );

    expect(rtlScreen.getByRole("combobox")).toHaveValue("");
  });

  it("keeps uncontrolled input when symbols update", () => {
    const { rerender } = renderWithSymbols(<SymbolSearch name="pair" />, [
      "BTCUSDT",
    ]);

    fireEvent.change(rtlScreen.getByRole("combobox"), {
      target: { value: "RAVE" },
    });

    expect(rtlScreen.getByRole("combobox")).toHaveValue("RAVE");

    rerender(
      <SymbolContext.Provider
        value={{
          ...mockSymbolContextValue,
          symbolsList: ["BTCUSDT", "RAVEUSDTM"],
        }}
      >
        <SymbolSearch name="pair" />
      </SymbolContext.Provider>,
    );

    expect(rtlScreen.getByRole("combobox")).toHaveValue("RAVE");
  });
});
