import { type FC } from "react"
import { Card } from "react-bootstrap"
import { LoginForm } from "../components/LoginForm"

export const LoginPage: FC<{}> = () => {

  return (
    <div className="d-flex justify-content-center align-items-center" style={{ height: "100vh" }}>
      <Card className="p-4">
        <Card.Body>
          <Card.Title className="p-2">Login</Card.Title>
          <LoginForm />
        </Card.Body>
      </Card>
    </div>
  )
}

export default LoginPage
