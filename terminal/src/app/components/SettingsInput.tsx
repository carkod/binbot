import { type FocusEvent, type FC } from "react"
import { Form } from "react-bootstrap"

type SettingsInputProps = {
  value?: string | number
  name?: string
  label: string
  handleChange?: (e: React.ChangeEvent<HTMLInputElement>) => void
  handleBlur?: (e: FocusEvent<HTMLInputElement>) => void
  errorMsg?: string
  infoText?: string
  type?: "text" | "number"
  register?: any
  required?: boolean
}

const SettingsInput: FC<SettingsInputProps> = ({
  value,
  name,
  label,
  handleChange,
  handleBlur,
  errorMsg,
  infoText,
  register,
  type = "text",
  required = false,
}): JSX.Element => {
  return (
    <Form.Group>
      <Form.Label htmlFor={name}>{label}</Form.Label>
      <Form.Control
        id={name}
        onChange={handleChange}
        onBlur={handleBlur}
        defaultValue={type === "number" ? String(value) : value}
        isInvalid={!!errorMsg}
        type={type}
        {...register(name, { required: required })}
      />
      {errorMsg && <Form.Control.Feedback>{errorMsg}</Form.Control.Feedback>}
      {infoText && (
        <Form.Control.Feedback tooltip>{infoText}</Form.Control.Feedback>
      )}
    </Form.Group>
  )
}

export default SettingsInput
