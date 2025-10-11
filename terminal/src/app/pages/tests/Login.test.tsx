import { render } from "@testing-library/react";
import { Provider } from "react-redux";
import { store } from "../../store";
import { MemoryRouter } from "react-router-dom";
import LoginPage from "../Login";

describe("Login page", () => {
  it("renders without crashing", () => {
    const { container } = render(
      <Provider store={store}>
        <MemoryRouter>
          <LoginPage />
        </MemoryRouter>
      </Provider>,
    );
    expect(container.querySelector(".card-title")).not.toBeNull();
  });
});
