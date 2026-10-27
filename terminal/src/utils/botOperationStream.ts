import { toast } from "react-toastify";
import { buildBackUrl } from "./api";
import type {
  BotOperationResponse,
  BotOperationStreamResult,
} from "./api.types";
import { getToken } from "./login";

export const streamBotOperation = async (
  url: string,
  operation: string,
): Promise<BotOperationStreamResult> => {
  const toastId = toast.info(`${operation} (0%)`, {
    autoClose: false,
    closeOnClick: false,
    hideProgressBar: false,
    progress: 0,
    theme: "colored",
  });
  try {
    const token = getToken();
    const response = await fetch(`${buildBackUrl()}${url}`, {
      method: "POST",
      headers: {
        Accept: "text/event-stream",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    });
    if (!response.ok) {
      throw new Error(`Bot operation failed (HTTP ${response.status})`);
    }
    if (!response.body) {
      throw new Error("The server did not provide a progress stream.");
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let result: BotOperationResponse | undefined;

    const consumeEvent = (block: string) => {
      const lines = block.split("\n");
      const event = lines.find((line) => line.startsWith("event: "))?.slice(7);
      const data = lines
        .filter((line) => line.startsWith("data: "))
        .map((line) => line.slice(6))
        .join("\n");
      if (!event || !data) return;
      const payload = JSON.parse(data);
      if (event === "progress") {
        const percent = Math.max(0, Math.min(100, payload.percent));
        toast.update(toastId, {
          render: `${payload.message} (${percent}%)`,
          progress: percent / 100,
        });
      } else if (event === "result") {
        result = payload.response as BotOperationResponse;
      } else if (event === "error") {
        throw new Error(payload.message);
      }
    };

    while (true) {
      const { value, done } = await reader.read();
      buffer += decoder.decode(value, { stream: !done });
      buffer = buffer.replace(/\r\n/g, "\n");
      let boundary = buffer.indexOf("\n\n");
      while (boundary >= 0) {
        consumeEvent(buffer.slice(0, boundary));
        buffer = buffer.slice(boundary + 2);
        boundary = buffer.indexOf("\n\n");
      }
      if (result || done) break;
    }

    if (!result) {
      throw new Error(
        "The progress stream ended before the result arrived. Refresh the bot before retrying.",
      );
    }
    if (result.error) {
      throw new Error(result.message);
    }
    toast.update(toastId, {
      render: result.message,
      type: "success",
      progress: null,
      autoClose: 5000,
    });
    return { data: { bot: result.data } };
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Bot operation failed";
    toast.update(toastId, {
      render: message,
      type: "error",
      progress: null,
      autoClose: 5000,
    });
    return { error: { status: "CUSTOM_ERROR", error: message } };
  }
};
