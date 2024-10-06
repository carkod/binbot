import { fetchBaseQuery } from "@reduxjs/toolkit/query"
import { getToken } from "./login"
import { Bounce, toast } from "react-toastify"
import {
  isRejectedWithValue,
  type Middleware,
  type MiddlewareAPI,
} from "@reduxjs/toolkit"

export function buildBackUrl() {
  let base = window.location.hostname.split(".")
  if (base.includes("localhost")) {
    base = ["localhost:8008"]
  } else {
    base.unshift("api")
  }
  const backUrl = `${window.location.protocol}//${base.join(".")}`
  return backUrl
}

export const baseQuery = fetchBaseQuery({
  baseUrl: buildBackUrl(),
  prepareHeaders: (headers, { getState }) => {
    const token = getToken()

    if (token) {
      headers.set("Authorization", `Bearer ${token}`)
    }
    return headers
  },
})

export const defaultResponseHandler = async (res: Response) => {
  const content = await res.json()
  return content.length ? JSON.parse(content) : null
}

export const defaultStatusValidator = (res: Response) => {
  if (res.status >= 200 && res.status < 300) {
    return true
  } else {
    return false
  }
}

export type NotificationType = "info" | "warning" | "success" | "error"

export const notifification = (message: string, type: NotificationType) => {
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
  })
}
