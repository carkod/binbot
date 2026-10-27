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
  expect(toast.info).toHaveBeenCalledWith(
    "Activating bot (0%)",
    expect.objectContaining({
      autoClose: false,
      hideProgressBar: false,
      progress: 0,
    }),
  );
  expect(toast.update).toHaveBeenCalledWith("bot-progress", {
    render: "Submitting the entry order (45%)",
    progress: 0.45,
  });
  expect(toast.update).toHaveBeenCalledWith("bot-progress", {
    render: "Activated",
    type: "success",
    progress: null,
    autoClose: 5000,
  });
  expect(toast.success).not.toHaveBeenCalled();
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
