import { render, screen as rtlScreen } from "@testing-library/react";
import "@testing-library/jest-dom";
import { filterSymbolByBaseAsset } from "../../utils/api";
import SymbolSearch from "./SymbolSearch";
import { vi } from "vitest";

vi.mock("../../features/autotradeApiSlice", () => ({
  useGetSettingsQuery: vi.fn(() => ({ data: {} })),
}));

describe("Search symbols", () => {
  it("returns symbols only with the given baseAsset", () => {
    const baseAsset = "USDC";
    const listSymbols = ["USDCBNB", "BTCUSDC", "BTCETH", "ETHUSDT", "ETHUSDC"];
    const symbols = filterSymbolByBaseAsset(listSymbols, baseAsset);
    expect(symbols).toEqual(["BTCUSDC", "ETHUSDC"]);
  });
});

describe("SymbolSearch component", () => {
  it("does not render label if not passed", () => {
    render(<SymbolSearch name="pair" options={["BTCUSDT"]} />);
    // Should not find any label element
    expect(rtlScreen.queryByText(/Select pair/i)).not.toBeInTheDocument();
  });

  it("renders label if passed", () => {
    render(
      <SymbolSearch name="pair" label="Select pair" options={["BTCUSDT"]} />
    );
    expect(rtlScreen.getByText("Select pair")).toBeInTheDocument();
  });

  it("renders placeholder if passed", () => {
    render(
      <SymbolSearch
        name="pair"
        options={["BTCUSDT"]}
        placeholder="Search by pair"
      />
    );
    expect(
      rtlScreen.getByPlaceholderText("Search by pair")
    ).toBeInTheDocument();
  });

  it("shows error message when errors object is passed", () => {
    render(
      <SymbolSearch
        name="pair"
        options={["BTCUSDT"]}
        errors={{ pair: "Invalid symbol" }}
        required={true}
      />
    );
    expect(rtlScreen.getByText("Invalid symbol")).toBeInTheDocument();
  });
});
