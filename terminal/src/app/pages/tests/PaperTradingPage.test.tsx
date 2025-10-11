import { render } from "@testing-library/react";
import { Provider } from "react-redux";
import { store } from "../../store";
import { MemoryRouter } from "react-router-dom";
import PaperTradingPage from "../PaperTradingPage";

describe("PaperTradingPage page", () => {
  it("renders without crashing", () => {
    const { container } = render(
      <Provider store={store}>
        <MemoryRouter>
          <PaperTradingPage />
        </MemoryRouter>
      </Provider>,
    );
    expect(container.querySelector(".container-fluid")).not.toBeNull();
  });
});
