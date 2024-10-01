import { fetchBaseQuery } from "@reduxjs/toolkit/query"
import { getToken } from "./login"

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
      headers.set("authorization", `Bearer ${token}`)
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