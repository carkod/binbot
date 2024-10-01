import { useActionData, useLocation, useNavigation } from "react-router"
import { LoginForm } from "../components/LoginForm"
import { getToken } from "../../utils/login"
import { useState, type FC } from "react"
import { SubmitHandler, useForm } from "react-hook-form"
import { Button, Card, Container, Row, Col } from "react-bootstrap"

interface LoginFormState {
  email: string
  password: string
}

export const LoginPage: FC<{}> = () => {
  let location = useLocation()
  let params = new URLSearchParams(location.search)
 

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
