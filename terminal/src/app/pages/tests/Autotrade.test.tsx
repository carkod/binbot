import { render } from "@testing-library/react";
import { Provider } from "react-redux";
import { store } from "../../store";
import { MemoryRouter } from "react-router-dom";
import Autotrade from "../Autotrade";

describe("Autotrade page", () => {
  it("renders without crashing", () => {
    const { container } = render(
      <Provider store={store}>
        <MemoryRouter>
          <Autotrade />
        </MemoryRouter>
      </Provider>,
    );
    expect(container.querySelector(".container")).not.toBeNull();
  });
});
