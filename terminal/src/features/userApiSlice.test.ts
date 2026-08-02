import { configureStore } from "@reduxjs/toolkit";
import { toast } from "react-toastify";
import { vi } from "vitest";
import { userApiSlice } from "./userApiSlice";

class MockRequest {
  url: string;
  init?: RequestInit;

  constructor(input: RequestInfo | URL, init?: RequestInit) {
    this.url = String(input);
    this.init = init;
  }

  clone() {
    return this;
  }
}

const makeApiStore = () =>
  configureStore({
    reducer: {
      [userApiSlice.reducerPath]: userApiSlice.reducer,
    },
    middleware: (getDefaultMiddleware) =>
      getDefaultMiddleware().concat(userApiSlice.middleware),
  });

describe("userApiSlice", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("shows an error toast when login returns an HTTP error", async () => {
    const toastSpy = vi.spyOn(toast, "error").mockImplementation(vi.fn());
    vi.stubGlobal("Request", MockRequest);
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        return new Response(JSON.stringify({ detail: "Method Not Allowed" }), {
          status: 405,
          statusText: "Method Not Allowed",
          headers: { "content-type": "application/json" },
        });
      }),
    );

    const store = makeApiStore();
    const formData = new FormData();
    formData.append("username", "carlos@example.com");
    formData.append("password", "password");

    await store.dispatch(userApiSlice.endpoints.postLogin.initiate(formData));

    expect(toastSpy).toHaveBeenCalledWith(
      "Method Not Allowed",
      expect.any(Object),
    );
  });

  it("rejects registerUser when the API returns an application-level error", async () => {
    const toastSpy = vi.spyOn(toast, "error").mockImplementation(vi.fn());
    vi.stubGlobal("Request", MockRequest);
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        return new Response(
          JSON.stringify({
            message: "Email already exists",
            error: 1,
          }),
          {
            status: 200,
            headers: { "content-type": "application/json" },
          },
        );
      }),
    );

    const store = makeApiStore();
    const result = await store.dispatch(
      userApiSlice.endpoints.registerUser.initiate({
        email: "carlos@example.com",
        is_active: true,
        role: "user",
        full_name: "Carlos",
        password: "password123",
        username: "carlos",
        description: "",
      }),
    );

    expect(result).toMatchObject({
      error: {
        status: "CUSTOM_ERROR",
        error: "Email already exists",
      },
    });
    expect(toastSpy).toHaveBeenCalledWith(
      "Email already exists",
      expect.any(Object),
    );
  });
});
