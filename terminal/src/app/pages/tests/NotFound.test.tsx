import { render } from "@testing-library/react";
import { Provider } from "react-redux";
import { store } from "../../store";
import { MemoryRouter } from "react-router-dom";
import NotFoundPage from "../NotFound";

describe("NotFound page", () => {
  it("renders without crashing", () => {
    const { container } = render(
      <Provider store={store}>
        <MemoryRouter>
          <NotFoundPage />
        </MemoryRouter>
      </Provider>,
    );
    expect(container.querySelector(".content")).not.toBeNull();
  });
});
