import { buildBackUrl } from "./api";

describe("buildBackUrl", () => {
  it("uses port 8008 for a staging machine hostname", () => {
    expect(
      buildBackUrl({
        hostname: "desktop-mkotse4",
        protocol: "http:",
      }),
    ).toBe("http://desktop-mkotse4:8008");
  });

  it("uses port 8008 for localhost", () => {
    expect(
      buildBackUrl({
        hostname: "localhost",
        protocol: "http:",
      }),
    ).toBe("http://localhost:8008");
  });

  it("uses the API subdomain for a deployed domain", () => {
    expect(
      buildBackUrl({
        hostname: "binbot.in",
        protocol: "https:",
      }),
    ).toBe("https://api.binbot.in");
  });
});
