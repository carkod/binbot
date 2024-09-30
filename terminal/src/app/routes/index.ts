import type { LoaderFunctionArgs } from "react-router-dom"
import { redirect } from "react-router-dom"
import { getToken } from "../../utils/login"

export async function loginAction({ request }: LoaderFunctionArgs) {
  let formData = await request.formData()
  let username = formData.get("username") as string | null
  // return null

  // Validate our form inputs and return validation errors via useActionData()
  if (!username) {
    return {
      error: "You must provide a username to log in",
    }
  }

  // Sign in and redirect to the proper destination if successful.
  // try {
  //   await fakeAuthProvider.signin(username)
  // } catch (error) {
  //   // Unused as of now but this is how you would handle invalid
  //   // username/password combinations - just like validating the inputs
  //   // above
  //   return {
  //     error: "Invalid login attempt",
  //   }
  // }

  // let redirectTo = formData.get("redirectTo") as string | null
  return redirect("/dashboard")
}

export async function loginLoader() {
  // if (fakeAuthProvider.isAuthenticated) {
  //   return redirect("/")
  // }
  // return null
  return redirect("/dashboard")
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
