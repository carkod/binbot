import "@testing-library/jest-dom";
import { MemoryRouter } from "react-router";
import { render, screen as rtlScreen } from "../../utils/render";
import Header from "./Header";

describe("Header", () => {
  it("renders the index route without passing an undefined path to matchPath", () => {
    render(
      <MemoryRouter initialEntries={["/"]}>
        <Header onExpand={() => undefined} />
      </MemoryRouter>,
    );

    expect(rtlScreen.getByText("Home")).toBeInTheDocument();
  });

  it("skips the pathless index route when matching another page", () => {
    render(
      <MemoryRouter initialEntries={["/bots"]}>
        <Header onExpand={() => undefined} />
      </MemoryRouter>,
    );

    expect(rtlScreen.getByText("Bots")).toBeInTheDocument();
  });
});
