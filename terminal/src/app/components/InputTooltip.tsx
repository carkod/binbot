import { type FC } from "react"
import { Button, Form } from "react-bootstrap"
import { Label } from "reactstrap"

interface InputTooltipProps {
  name: string
  tooltip: string
  children: React.ReactNode
  title: string

}

export const InputTooltip: FC<InputTooltipProps> = ({ name, tooltip, children }, ...props) => {
  return (
    <Form.Group className="position-relative">
      <Form.Label htmlFor={name}>
        <Button type="button" className="btn--tooltip" id={`${name}-tooltip`}>
          {children}
        </Button>
      </Form.Label>
      <Form.Control.Feedback>
        <small>{tooltip}</small>
      </Form.Control.Feedback>
    </Form.Group>
  )
}

export default InputTooltip
