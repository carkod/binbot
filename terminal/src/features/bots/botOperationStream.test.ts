import { vi } from "vitest";
import { toast } from "react-toastify";
import { makeStore } from "../../app/store";
import { botsApiSlice } from "./botsApiSlice";

vi.mock("react-toastify", () => ({
  Bounce: vi.fn(),
  toast: {
    info: vi.fn(() => "bot-progress"),
    update: vi.fn(),
    success: vi.fn(),
    error: vi.fn(),
  },
}));

afterEach(() => {
  vi.unstubAllGlobals();
  vi.clearAllMocks();
});

it("activates without a percentage toast and waits for the final bot response", async () => {
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
  expect(toast.info).not.toHaveBeenCalled();
  expect(toast.update).not.toHaveBeenCalled();
  expect(toast.success).toHaveBeenCalledWith("Activated");
  expect(fetch).toHaveBeenCalledWith(
    expect.stringContaining("/bot-1"),
    expect.objectContaining({
      method: "POST",
      headers: expect.objectContaining({ Accept: "text/event-stream" }),
    }),
  );
});

it("shows activation errors without creating a progress toast", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockRejectedValue(new Error("Network failed")),
  );

  const result = await makeStore().dispatch(
    botsApiSlice.endpoints.activateBot.initiate("bot-1"),
  );

  expect(result.error).toMatchObject({ status: "CUSTOM_ERROR" });
  expect(toast.info).not.toHaveBeenCalled();
  expect(toast.error).toHaveBeenCalledWith("Network failed");
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
  expect(toast.info).toHaveBeenCalledWith(
    "Closing bot (0%)",
    expect.objectContaining({ progress: 0 }),
  );
  expect(toast.update).toHaveBeenCalledWith(
    "bot-progress",
    expect.objectContaining({
      type: "error",
      render: expect.stringContaining("stream ended before the result"),
    }),
  );
});
