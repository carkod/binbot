import { type FC } from "react"
import { Button } from "react-bootstrap"

export type LightSwitchProps = {
  value: 0 | 1
  name: string
  toggle: (name: string, value: 0 | 1) => void
}

/**
 * Standard toggler that accepts 1 (on) and 0 (off)
 * @param {*} value: boolean integer 0 for off or 1 for on
 * @returns React.Component
 */
const LightSwitch: FC<LightSwitchProps> = ({ value, name, toggle }, props) => {
  return (
    <Button
      name={name}
      color={value === 1 ? "success" : "secondary"}
      onClick={e => toggle(name, value)}
      {...props}
    >
      {value === 1 ? "On" : "Off"}
    </Button>
  )
}

export default LightSwitch
