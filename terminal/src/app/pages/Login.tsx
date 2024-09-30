import { useActionData, useLocation, useNavigation } from "react-router"
import { LoginForm } from "../components/LoginForm"
import { getToken } from "../../utils/login"
import type { FC } from "react"

export const LoginPage: FC<{}> = () => {
  let location = useLocation()
  const navigate = useNavigation()
  let params = new URLSearchParams(location.search)
  let from = params.get("from") || "/"

  let navigation = useNavigation()
  let isLoggingIn = getToken()

  let actionData = useActionData() as { error: string } | undefined

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    let formData = new FormData(e.currentTarget)
    console.log(formData)
    // navigate("/bots", formData)
  }

  return (
    <div>
      <div className="content">
        <h1>Login</h1>
        <LoginForm handleSubmit={handleSubmit} />
      </div>
    </div>
  )
}

export default LoginPage;
