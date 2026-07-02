import { fetchBaseQuery } from "@reduxjs/toolkit/query";
import { Bounce, toast } from "react-toastify";
import { getToken, removeToken } from "./login";

/**
 * Builds the backend URL based on the current location.
 * This is dependant on infrastructure, so don't change unless infra changes
 */
export function buildBackUrl(
  location: Pick<Location, "hostname" | "port" | "protocol"> = window.location,
) {
  if (location.port === "8007") {
    return "/api";
  }

  const host = location.hostname.includes(".")
    ? `api.${location.hostname}`
    : `${location.hostname}:8008`;
  return `${location.protocol}//${host}`;
}

export const binbotBaseQuery = async (
  args: any,
  api: any,
  extraOptions: any,
) => {
  const baseQuery = fetchBaseQuery({
    baseUrl: buildBackUrl(),
    prepareHeaders: (headers) => {
      const token = getToken();

      if (token) {
        headers.set("Authorization", `Bearer ${token}`);
      }
      return headers;
    },
  });

  const result = await baseQuery(args, api, extraOptions);

  if (result?.error?.status === 401) {
    removeToken();
  }
  return result;
};

export const binanceBaseQuery = fetchBaseQuery({
  baseUrl: "https://api.binance.com/api/v3",
});

export const defaultResponseHandler = async (res: Response) => {
  const content = await res.json();
  return content.length ? JSON.parse(content) : null;
};

export const defaultStatusValidator = (res: Response) => {
  if (res.status >= 200 && res.status < 300) {
    return true;
  } else {
    return false;
  }
};

export type NotificationType = "info" | "warning" | "success" | "error";

const apiErrorMessageFromData = (data: unknown): string | undefined => {
  if (typeof data === "string") {
    return data;
  }

  if (!data || typeof data !== "object") {
    return undefined;
  }

  const payload = data as {
    detail?: unknown;
    message?: unknown;
    error?: unknown;
  };

  if (typeof payload.message === "string") {
    return payload.message;
  }

  if (typeof payload.detail === "string") {
    return payload.detail;
  }

  if (Array.isArray(payload.detail)) {
    return payload.detail
      .map((detail) => {
        if (typeof detail === "string") {
          return detail;
        }
        if (
          detail &&
          typeof detail === "object" &&
          "msg" in detail &&
          typeof detail.msg === "string"
        ) {
          return detail.msg;
        }
        return undefined;
      })
      .filter(Boolean)
      .join(", ");
  }

  if (typeof payload.error === "string") {
    return payload.error;
  }

  return undefined;
};

export const getApiErrorMessage = (
  error: unknown,
  fallback = "Request failed",
): string => {
  const candidate =
    error && typeof error === "object" && "error" in error
      ? (error as { error?: unknown }).error
      : error;

  if (candidate && typeof candidate === "object") {
    if ("data" in candidate) {
      const dataMessage = apiErrorMessageFromData(candidate.data);
      if (dataMessage) {
        return dataMessage;
      }
    }

    if (
      "message" in candidate &&
      typeof (candidate as { message?: unknown }).message === "string"
    ) {
      return (candidate as { message: string }).message;
    }

    if ("status" in candidate) {
      return `${fallback} (${String(candidate.status)})`;
    }
  }

  return fallback;
};

export const notifification = (type: NotificationType, message: string) => {
  return toast[type](message, {
    position: "top-right",
    autoClose: 5000,
    hideProgressBar: true,
    closeOnClick: false,
    pauseOnHover: true,
    draggable: false,
    progress: undefined,
    theme: "colored",
    transition: Bounce,
  });
};

// Filter by base asset (fiat) provided by autotrade settings
// This is done in the front-end because it doesn't matter in the back-end, we always get the full list of symbols
export const filterSymbolByBaseAsset = (
  options: string[],
  baseAsset: string,
): string[] => {
  return options.filter((item) => item.endsWith(baseAsset));
};
