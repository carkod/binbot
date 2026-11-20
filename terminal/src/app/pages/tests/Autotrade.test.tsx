import userEvent from "@testing-library/user-event";
import { Provider } from "react-redux";
import { MemoryRouter } from "react-router";
import { vi } from "vitest";
import {
  initialAutotradeSettings,
  setSettings,
} from "../../../features/autotradeSlice";
import { render, screen as rtlScreen, waitFor } from "../../../utils/render";
import { makeStore } from "../../store";
import Autotrade from "../Autotrade";

const updateSettings = vi.hoisted(() =>
  vi.fn(() => ({ unwrap: vi.fn().mockResolvedValue({}) })),
);

vi.mock("../../../features/autotradeApiSlice", async () => {
  const actual = await vi.importActual("../../../features/autotradeApiSlice");

  return {
    ...actual,
    useGetSettingsQuery: vi.fn(() => ({ data: undefined })),
    useEditSettingsMutation: vi.fn(() => [updateSettings]),
  };
});

const renderAutotradePage = (
  overrides: Partial<typeof initialAutotradeSettings> = {},
) => {
  const store = makeStore();

  store.dispatch(setSettings({ ...initialAutotradeSettings, ...overrides }));

  return {
    store,
    ...render(
      <Provider store={store}>
        <MemoryRouter>
          <Autotrade />
        </MemoryRouter>
      </Provider>,
    ),
  };
};

const enableGridLadders = async () => {
  const user = userEvent.setup();

  const toggle = rtlScreen.getByRole("switch", { name: /Enable grid ladders/ });

  await user.click(toggle as HTMLElement);
};

describe("Autotrade page", () => {
  beforeEach(() => updateSettings.mockClear());

  it("renders without crashing", () => {
    const { container } = renderAutotradePage();

    expect(
      rtlScreen.getByRole("heading", { name: "General bot autotrade" }),
    ).toBeInTheDocument();
  });

  it("hides grid ladder fields until enable_grid_ladders is toggled on", () => {
    renderAutotradePage();

    expect(rtlScreen.getByText("Grid trading")).toBeTruthy();
    expect(rtlScreen.getByLabelText("Enable grid ladders?")).toBeTruthy();
    [
      "Grid allocation pct",
      "Grid cash reserve pct",
      "Grid total margin",
      "Grid level count",
      "Grid max active ladders",
      "Max margin per ladder pct",
    ].forEach((label) => {
      expect(rtlScreen.queryByLabelText(label)).toBeNull();
    });
  });

  it("reveals grid trading settings once enable_grid_ladders is on", async () => {
    renderAutotradePage();
    await enableGridLadders();

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

  it("uses grid trading defaults from the autotrade slice", async () => {
    renderAutotradePage();
    await enableGridLadders();

    expect(
      (rtlScreen.getByLabelText("Grid allocation pct") as HTMLInputElement)
        .value,
    ).toBe(String(initialAutotradeSettings.grid_allocation_pct * 100));
    expect(
      (rtlScreen.getByLabelText("Grid cash reserve pct") as HTMLInputElement)
        .value,
    ).toBe(String(initialAutotradeSettings.grid_cash_reserve_pct * 100));
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
    ).toBe(String(initialAutotradeSettings.max_margin_per_ladder_pct * 100));
  });

  it("allows fractional grid trading values", async () => {
    renderAutotradePage();
    await enableGridLadders();

    [
      "Grid allocation pct",
      "Grid cash reserve pct",
      "Grid total margin",
      "Max margin per ladder pct",
    ].forEach((label) => {
      expect((rtlScreen.getByLabelText(label) as HTMLInputElement).step).toBe(
        "any",
      );
    });
  });

  it("keeps grid count fields on whole-number steps", async () => {
    renderAutotradePage();
    await enableGridLadders();

    ["Grid level count", "Grid max active ladders"].forEach((label) => {
      expect((rtlScreen.getByLabelText(label) as HTMLInputElement).step).toBe(
        "1",
      );
    });
  });

  it("edits grid percentages and saves their stored ratios", async () => {
    const user = userEvent.setup();

    const { store } = renderAutotradePage({ enable_grid_ladders: true });

    const allocation = rtlScreen.getByLabelText("Grid allocation pct");

    await user.clear(allocation);
    await user.type(allocation, "65.5");
    await user.tab();
    expect(
      store.getState().autotradeSettings.settings.grid_allocation_pct,
    ).toBe(0.655);
    expect((allocation as HTMLInputElement).value).toBe("65.5");

    const reserve = rtlScreen.getByLabelText("Grid cash reserve pct");

    await user.clear(reserve);
    await user.type(reserve, "0");
    await user.tab();
    expect(
      store.getState().autotradeSettings.settings.grid_cash_reserve_pct,
    ).toBe(0);

    const perLadder = rtlScreen.getByLabelText("Max margin per ladder pct");

    await user.clear(perLadder);
    await user.type(perLadder, "25.5");
    await user.tab();
    expect(
      store.getState().autotradeSettings.settings.max_margin_per_ladder_pct,
    ).toBe(0.255);
    await user.click(rtlScreen.getByRole("button", { name: "Save" }));

    await waitFor(() =>
      expect(updateSettings).toHaveBeenCalledWith(
        expect.objectContaining({
          grid_allocation_pct: 0.655,
          grid_cash_reserve_pct: 0,
          max_margin_per_ladder_pct: 0.255,
        }),
      ),
    );
  });

  it("preserves stored ratios when saving while grid controls are hidden", async () => {
    const user = userEvent.setup();

    renderAutotradePage();
    await user.click(rtlScreen.getByRole("button", { name: "Save" }));

    await waitFor(() =>
      expect(updateSettings).toHaveBeenCalledWith(
        expect.objectContaining({
          grid_allocation_pct: initialAutotradeSettings.grid_allocation_pct,
          grid_cash_reserve_pct: initialAutotradeSettings.grid_cash_reserve_pct,
          max_margin_per_ladder_pct:
            initialAutotradeSettings.max_margin_per_ladder_pct,
        }),
      ),
    );
  });
});
