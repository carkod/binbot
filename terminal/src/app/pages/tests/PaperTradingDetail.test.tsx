import { render } from "@testing-library/react";
import { Provider } from "react-redux";
import { store } from "../../store";
import { MemoryRouter } from "react-router-dom";
import PaperTradingDetailPage from "../PaperTradingDetail";

describe("PaperTradingDetail page", () => {
  it("renders without crashing", () => {
    const { container } = render(
      <Provider store={store}>
        <MemoryRouter>
          <PaperTradingDetailPage />
        </MemoryRouter>
      </Provider>,
    );
    expect(container.querySelector(".card-header")).not.toBeNull();
  });
});
