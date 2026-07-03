import { buildBackUrl } from "./api";

describe("buildBackUrl", () => {
  it("uses the API path for a staging machine hostname", () => {
    expect(
      buildBackUrl({
        hostname: "staging-binbot",
        port: "8007",
        protocol: "http:",
      }),
    ).toBe("http://staging-binbot/api");
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
