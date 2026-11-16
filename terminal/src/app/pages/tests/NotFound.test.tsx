import { Provider } from "react-redux";
import { MemoryRouter } from "react-router";
import { render } from "../../../utils/render";
import { store } from "../../store";
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
