import { vi } from "vitest";
import { fetchBinquantStrategyNames } from "./useBinquantStrategyNames";

const jsonResponse = (data: unknown) =>
  ({
    json: vi.fn().mockResolvedValue(data),
    ok: true,
  }) as unknown as Response;

const textResponse = (data: string) =>
  ({
    ok: true,
    text: vi.fn().mockResolvedValue(data),
  }) as unknown as Response;

describe("fetchBinquantStrategyNames", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("discovers top-level, nested, and declared strategy names", async () => {
    const fetchMock = vi.fn((input: string | URL | Request) => {
      const url = input.toString();

      if (url.includes("git/trees/master?recursive=1")) {
        return Promise.resolve(
          jsonResponse({
            tree: [
              {
                path: "strategies/top_gainer_early_momentum.py",
                type: "blob",
              },
              {
                path: "strategies/grid/ladder_deployer.py",
                type: "blob",
              },
              { path: "tests/test_strategy.py", type: "blob" },
            ],
          }),
        );
      }

      if (url.endsWith("top_gainer_early_momentum.py")) {
        return Promise.resolve(
          textResponse(
            'class Strategy:\n    ALGO = "top_gainer_early_momentum"',
          ),
        );
      }

      if (url.endsWith("ladder_deployer.py")) {
        return Promise.resolve(
          textResponse('class Strategy:\n    ALGO = "grid_ladder"'),
        );
      }

      throw new Error(`Unexpected URL: ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    const names = await fetchBinquantStrategyNames(
      new AbortController().signal,
    );

    expect(names).toEqual(
      new Set([
        "top_gainer_early_momentum",
        "ladder_deployer",
        "grid_ladder_deployer",
        "grid_ladder",
      ]),
    );
  });
});
