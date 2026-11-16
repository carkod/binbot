import { MemoryRouter } from "react-router";
import { render, screen } from "../../utils/render";
import Sidebar from "./Sidebar";

describe("Sidebar", () => {
  it.each([
    ["/bots", "Bots"],
    ["/bots/futures/new/ARIAUSDTM", "New Futures Bot"],
    ["/bots/new/BTCUSDT", "New Bot"],
    ["/bots/futures/edit/example", "Bots"],
  ])("selects the most specific navigation item for %s", (path, name) => {
    render(
      <MemoryRouter initialEntries={[path]}>
        <Sidebar />
      </MemoryRouter>,
    );

    const selectedLinks = screen
      .getAllByRole("link")
      .filter((link) => link.hasAttribute("data-active"));

    expect(selectedLinks).toEqual([screen.getByRole("link", { name })]);
    expect(selectedLinks[0]).toHaveAttribute("aria-current", "page");
  });
});
