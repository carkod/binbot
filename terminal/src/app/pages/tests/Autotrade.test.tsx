import { render, screen as rtlScreen } from "@testing-library/react";
import { Provider } from "react-redux";
import { makeStore } from "../../store";
import { MemoryRouter } from "react-router-dom";
import Autotrade from "../Autotrade";
import { initialAutotradeSettings } from "../../../features/autotradeSlice";
import { vi } from "vitest";

vi.mock("../../../features/autotradeApiSlice", async () => {
  const actual = await vi.importActual("../../../features/autotradeApiSlice");
  return {
    ...actual,
    useGetSettingsQuery: vi.fn(() => ({ data: undefined })),
    useEditSettingsMutation: vi.fn(() => [vi.fn()]),
  };
});

const renderAutotradePage = () =>
  render(
    <Provider store={makeStore()}>
      <MemoryRouter>
        <Autotrade />
      </MemoryRouter>
    </Provider>,
  );

describe("Autotrade page", () => {
  it("renders without crashing", () => {
    const { container } = renderAutotradePage();

    expect(container.querySelector(".container")).not.toBeNull();
  });

  it("renders grid trading settings", () => {
    renderAutotradePage();

    expect(rtlScreen.getByText("Grid trading")).toBeTruthy();
    [
      "Grid allocation pct",
      "Grid cash reserve pct",
      "Grid total margin",
      "Grid level count",
      "Grid max active ladders",
      "Max margin per ladder pct",
    ].forEach((label) => {
      expect(rtlScreen.getByLabelText(label)).toBeTruthy();
    });
  });

  it("uses grid trading defaults from the autotrade slice", () => {
    renderAutotradePage();

    expect(
      (rtlScreen.getByLabelText("Grid allocation pct") as HTMLInputElement)
        .value,
    ).toBe(String(initialAutotradeSettings.grid_allocation_pct));
    expect(
      (rtlScreen.getByLabelText("Grid cash reserve pct") as HTMLInputElement)
        .value,
    ).toBe(String(initialAutotradeSettings.grid_cash_reserve_pct));
    expect(
      (rtlScreen.getByLabelText("Grid total margin") as HTMLInputElement).value,
    ).toBe(String(initialAutotradeSettings.grid_total_margin));
    expect(
      (rtlScreen.getByLabelText("Grid level count") as HTMLInputElement).value,
    ).toBe(String(initialAutotradeSettings.grid_level_count));
    expect(
      (rtlScreen.getByLabelText("Grid max active ladders") as HTMLInputElement)
        .value,
    ).toBe(String(initialAutotradeSettings.grid_max_active_ladders));
    expect(
      (
        rtlScreen.getByLabelText(
          "Max margin per ladder pct",
        ) as HTMLInputElement
      ).value,
    ).toBe(String(initialAutotradeSettings.max_margin_per_ladder_pct));
  });
});
