import { type FC } from "react"
import { Form } from "react-bootstrap"

type SettingsInputProps = {
  value: string | number
  name: string
  label: string
  handleChange?: (e: React.ChangeEvent<HTMLInputElement>) => void
  handleBlur?: (e: React.FocusEvent<HTMLInputElement>) => void
  errorMsg?: string
  infoText?: string
  type?: "text" | "number"
}

const SettingsInput: FC<SettingsInputProps> = ({
  value,
  name,
  label,
  handleChange,
  handleBlur,
  errorMsg,
  infoText,
  type = "text",
}, ...props): JSX.Element => {
  return (
    <Form.Group>
      <Form.Label for={name}>{label}</Form.Label>
      <Form.Control
        name={name}
        id={name}
        onChange={handleChange}
        onBlur={handleBlur}
        defaultValue={type === "number" ? String(value) : value}
        isInvalid={!!errorMsg}
        type={type}
        {...props}
      />
      {errorMsg && <Form.Control.Feedback>{errorMsg}</Form.Control.Feedback>}
      {infoText && (
        <Form.Control.Feedback tooltip>Looks good!</Form.Control.Feedback>
      )}
    </Form.Group>
  )
}

export default SettingsInput
