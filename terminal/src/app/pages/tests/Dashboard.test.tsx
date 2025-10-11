import { render } from "@testing-library/react";
import { Provider } from "react-redux";
import { store } from "../../store";
import { MemoryRouter } from "react-router-dom";
import DashboardPage from "../Dashboard";

describe("Dashboard page", () => {
  it("renders without crashing", () => {
    const { container } = render(
      <Provider store={store}>
        <MemoryRouter>
          <DashboardPage />
        </MemoryRouter>
      </Provider>,
    );
    expect(container.querySelector(".content")).not.toBeNull();
  });
});
