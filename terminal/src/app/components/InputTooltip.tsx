import { type FC } from "react"
import { Form } from "react-bootstrap"
import { type FieldErrors } from "react-hook-form"
import { type Bot } from "../../features/bots/botInitialState"

interface InputTooltipProps {
  name: string
  tooltip: string
  children: React.ReactNode
  label: string
  errors: FieldErrors<Bot>
  required?: boolean
}

export const InputTooltip: FC<InputTooltipProps> = (
  { name, tooltip, label, children, errors, required = false }) => {
  return (
    <Form.Group className="position-relative">
      <Form.Label htmlFor={name}>
        {label}
        {required && <span className="u-required">*</span>}
      </Form.Label>
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
