import { vi } from "vitest";
import { makeStore } from "../../app/store";
import { singleBot } from "./botInitialState";
import { botsApiSlice } from "./botsApiSlice";

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

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

it("returns the edited bot from the API data field so Deal can activate it", async () => {
  const bot = { ...singleBot, id: "bot-1" };
  vi.stubGlobal("Request", MockRequest);
  const fetchMock = vi.fn(
    async () =>
      new Response(
        JSON.stringify({
          message: "Successfully edited bot.",
          error: 0,
          data: bot,
        }),
        { status: 200, headers: { "content-type": "application/json" } },
      ),
  );
  vi.stubGlobal("fetch", fetchMock);

  const result = await makeStore().dispatch(
    botsApiSlice.endpoints.editBot.initiate({ id: bot.id, body: bot }),
  );

  expect(result.data).toEqual({ bot });
  expect(fetchMock).toHaveBeenCalledOnce();
});
