import { type FC } from "react"
import { Form } from "react-bootstrap"
import { Label } from "reactstrap"

interface InputTooltipProps {
  name: string
  text: string
  children: React.ReactNode
}

export const InputTooltip: FC<InputTooltipProps> = ({ name, text, children }, ...props) => {
  return (
    <Form.Group className="position-relative" controlId={`${name}-tooltip`}>
      <Label htmlFor={name}>
        <button type="button" className="btn--tooltip" id={`${name}-tooltip`}>
          {children}
        </button>
      </Label>
      <Form.Control.Feedback>
        <small>{text}</small>
      </Form.Control.Feedback>
    </Form.Group>
  )
}

export default InputTooltip
