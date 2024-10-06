import type { FC } from "react"
import { useEffect } from "react"
import { Form } from "react-bootstrap"
import { useForm } from "react-hook-form"
import { type LoginFormState } from "../components/LoginForm"

export const BotDetail: FC<{}> = () => {

	const {
    register,
    watch,
    formState: { errors },
  } = useForm<LoginFormState>({
    mode: "onTouched",
    reValidateMode: "onSubmit",
    defaultValues: {
      email: "",
      password: "",
    },
  })

	useEffect(() => {
    const subscription = watch((value, { name, type }) => {
      console.log(">>", value, name, type)
    })

    return () => subscription.unsubscribe()
  }, [watch])

  return (
    <div>
      <div className="content">
        <Form.Group className="mb-3" controlId="formBasicEmail">
          <Form.Label className="p-2">Email</Form.Label>
          <Form.Control
            className="p-2"
            type="email"
            placeholder="Enter email"
            {...register("email", {
              required: "Email is required",
              pattern: {
                value:
                  /^(([^<>()[\]\\.,;:\s@"]+(\.[^<>()[\]\\.,;:\s@"]+)*)|(".+"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$/,
                message: "Please enter a valid email",
              },
            })}
          />
          {errors.email && (
            <Form.Text className="text-danger">
              {errors.email.message}
            </Form.Text>
          )}
        </Form.Group>

        <Form.Group className="mb-3" controlId="formBasicPassword">
          <Form.Label className="p-2">Password</Form.Label>
          <Form.Control
            className="p-2"
            type="password"
            placeholder="Password"
            {...register("password", { required: "Password is required" })}
          />
          {errors.password && (
            <Form.Text className="text-danger">
              {errors.password.message}
            </Form.Text>
          )}
        </Form.Group>

      </div>
    </div>
  )
}

export default BotDetail
