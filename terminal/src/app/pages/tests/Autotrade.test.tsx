import userEvent from "@testing-library/user-event";
import { Provider } from "react-redux";
import { MemoryRouter } from "react-router";
import { vi } from "vitest";
import { initialAutotradeSettings } from "../../../features/autotradeSlice";
import { render, screen as rtlScreen } from "../../../utils/render";
import { makeStore } from "../../store";
import Autotrade from "../Autotrade";

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

const enableGridLadders = async () => {
  const user = userEvent.setup();

  const toggle = rtlScreen.getByRole("switch", { name: /Enable grid ladders/ });

  await user.click(toggle as HTMLElement);
};

describe("Autotrade page", () => {
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
});
