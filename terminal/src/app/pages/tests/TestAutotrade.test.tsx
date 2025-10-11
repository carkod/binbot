import { render } from "@testing-library/react";
import { Provider } from "react-redux";
import { store } from "../../store";
import { MemoryRouter } from "react-router-dom";
import TestAutotradePage from "../TestAutotrade";

describe("TestAutotrade page", () => {
  it("renders without crashing", () => {
    const { container } = render(
      <Provider store={store}>
        <MemoryRouter>
          <TestAutotradePage />
        </MemoryRouter>
      </Provider>,
    );
    expect(container.querySelector(".card-title")).not.toBeNull();
  });
});
