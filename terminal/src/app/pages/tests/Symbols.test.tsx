import { Provider } from "react-redux";
import { MemoryRouter } from "react-router";
import { render } from "../../../utils/render";
import { store } from "../../store";
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
