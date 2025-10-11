import { render } from "@testing-library/react";
import { Provider } from "react-redux";
import { store } from "../../store";
import { MemoryRouter } from "react-router-dom";
import SymbolsPage from "../Symbols";

describe("Symbols page", () => {
  it("renders without crashing", () => {
    const { container } = render(
      <Provider store={store}>
        <MemoryRouter>
          <SymbolsPage />
        </MemoryRouter>
      </Provider>,
    );
    expect(container.querySelector(".content")).not.toBeNull();
  });
});
