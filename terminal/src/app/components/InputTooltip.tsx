import { type FC } from "react"
import { Form } from "react-bootstrap"
import { type FieldErrors } from "react-hook-form"
import { type Bot } from "../../features/bots/botInitialState"

interface InputTooltipProps {
  name: string
  tooltip: string
  children: React.ReactNode
  title: string
  label: string
  errors: FieldErrors<Bot>
}

export const InputTooltip: FC<InputTooltipProps> = (
  { name, tooltip, label, children, errors },
  ...props
) => {
  return (
    <Form.Group className="position-relative">
      <Form.Label htmlFor={name}>{label}</Form.Label>
      {children}
      <Form.Control.Feedback>
        <small>{tooltip}</small>
      </Form.Control.Feedback>
      {errors[name] && (
        <Form.Control.Feedback type="invalid">
          {errors[name as keyof FieldErrors].message}
        </Form.Control.Feedback>
      )}
    </Form.Group>
  )
}

export default InputTooltip
