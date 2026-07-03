import { vi } from "vitest";
import { binbotBaseQuery, buildBackUrl, getApiErrorMessage } from "./api";

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

describe("buildBackUrl", () => {
  it("uses the same-origin API path for the staging hostname on the terminal port", () => {
    expect(
      buildBackUrl({
        hostname: "staging-binbot",
        port: "8007",
        protocol: "http:",
      }),
    ).toBe("/api");
  });

  it("uses the same-origin API path for a staging machine hostname on port 80", () => {
    expect(
      buildBackUrl({
        hostname: "staging-binbot",
        port: "",
        protocol: "http:",
      }),
    ).toBe("/api");
  });

  it("uses port 8008 for non-staging machine hostnames on the terminal port", () => {
    expect(
      buildBackUrl({
        hostname: "desktop-mkotse4",
        port: "8007",
        protocol: "http:",
      }),
    ).toBe("http://desktop-mkotse4:8008");
  });

  it("uses port 8008 for localhost", () => {
    expect(
      buildBackUrl({
        hostname: "localhost",
        port: "5173",
        protocol: "http:",
      }),
    ).toBe("http://localhost:8008");
  });

  it("uses port 8008 for loopback IP hosts", () => {
    expect(
      buildBackUrl({
        hostname: "127.0.0.1",
        port: "5173",
        protocol: "http:",
      }),
    ).toBe("http://127.0.0.1:8008");
  });

  it("uses the API subdomain for a deployed domain", () => {
    expect(
      buildBackUrl({
        hostname: "binbot.in",
        port: "",
        protocol: "https:",
      }),
    ).toBe("https://api.binbot.in");
  });
});

describe("getApiErrorMessage", () => {
  it("reads FastAPI detail messages from RTK query errors", () => {
    expect(
      getApiErrorMessage(
        {
          error: {
            status: 405,
            data: { detail: "Method Not Allowed" },
          },
        },
        "Login failed",
      ),
    ).toBe("Method Not Allowed");
  });

  it("falls back to a status-qualified message when no payload message exists", () => {
    expect(
      getApiErrorMessage(
        {
          error: {
            status: 405,
            data: {},
          },
        },
        "Login failed",
      ),
    ).toBe("Login failed (405)");
  });
});

describe("binbotBaseQuery", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    window.localStorage.clear();
    window.history.pushState({}, "", "/");
  });

  it("removes an expired token when the API returns unauthorized", async () => {
    window.history.pushState({}, "", "/login");
    window.localStorage.setItem("binbot-token", JSON.stringify("expired"));
    vi.stubGlobal("Request", MockRequest);
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        return new Response(
          JSON.stringify({ detail: "Credentials are invalid" }),
          {
            status: 401,
            statusText: "Unauthorized",
            headers: { "content-type": "application/json" },
          },
        );
      }),
    );

    await binbotBaseQuery("/users", {}, {});

    expect(window.localStorage.getItem("binbot-token")).toBeNull();
  });
});
