import { vi } from "vitest";
import { makeStore } from "../../app/store";
import { botsApiSlice } from "./botsApiSlice";

afterEach(() => vi.unstubAllGlobals());

it("reads split progress events and waits for the final bot response", async () => {
  const chunks = [
    'event: progress\ndata: {"percent": 45, "message": "Submitting',
    ' the entry order"}\n\nevent: result\ndata: {"percent": 100, "response":',
    ' {"message": "Activated", "error": 0, "data": {"id": "bot-1"}}}\n\n',
  ];
  const read = vi.fn();
  for (const chunk of chunks) {
    read.mockResolvedValueOnce({
      value: new TextEncoder().encode(chunk),
      done: false,
    });
  }
  read.mockResolvedValueOnce({ done: true });
  vi.stubGlobal(
    "fetch",
    vi
      .fn()
      .mockResolvedValue({ ok: true, body: { getReader: () => ({ read }) } }),
  );

  const store = makeStore();
  const result = await store.dispatch(
    botsApiSlice.endpoints.activateBot.initiate("bot-1"),
  );

  expect(result.data?.bot.id).toBe("bot-1");
  expect(store.getState().layout.botProgress?.percent).toBe(100);
  expect(fetch).toHaveBeenCalledWith(
    expect.stringContaining("/bot-1"),
    expect.objectContaining({
      method: "POST",
      headers: expect.objectContaining({ Accept: "text/event-stream" }),
    }),
  );
});

it("reports an uncertain outcome when the stream ends without a result", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: true,
      body: { getReader: () => ({ read: async () => ({ done: true }) }) },
    }),
  );

  const result = await makeStore().dispatch(
    botsApiSlice.endpoints.deactivateBot.initiate("bot-1"),
  );

  expect(result.error).toMatchObject({ status: "CUSTOM_ERROR" });
});
