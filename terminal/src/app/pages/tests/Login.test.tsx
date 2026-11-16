import { Provider } from "react-redux";
import { MemoryRouter } from "react-router";
import { render } from "../../../utils/render";
import { store } from "../../store";
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
    expect(container.querySelector("h4")?.textContent).toBe("Login");
  });
});
