import type { LoaderFunctionArgs } from "react-router-dom"
import { redirect } from "react-router-dom"
import { getToken } from "../../utils/login"

export async function loginAction({ request }: LoaderFunctionArgs) {
  let formData = await request.formData()
  let username = formData.get("username") as string | null
  let password = formData.get("password") as string | null

  console.log("username", username)
  console.log("password", password)


  // Validate our form inputs and return validation errors via useActionData()
  // if (!username) {
  //   return {
  //     error: "You must provide a username to log in",
  //   }
  // } else {
  //   return null
  // }
  return null;

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
}

export async function loginLoader() {
  const token = getToken();
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
