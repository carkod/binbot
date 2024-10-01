import type { LoaderFunctionArgs } from "react-router-dom"
import { redirect } from "react-router-dom"
import { getToken } from "../../utils/login"

export async function loginAction({ request }: LoaderFunctionArgs) {
  const token = getToken()
  if (token) {
    return redirect("/dashboard")
  } else {
    return null
  }

}

export async function loginLoader() {
  const token = getToken()
  if (token) {
    return redirect("/dashboard")
  } else {
    return null
  }
}

export function protectedLoader({ request }: LoaderFunctionArgs) {
  const token = getToken()

  if (token) {
    let params = new URLSearchParams()
    params.set("from", new URL(request.url).pathname)
    return redirect("/login?" + params.toString())
  }
  return null
}
