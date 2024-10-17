import { type FC } from "react"
import { Button, ToggleButton, ToggleButtonGroup } from "react-bootstrap"

export type LightSwitchProps = {
  value: 0 | 1
  name: string
  toggle?: (name: string, value: 0 | 1) => void
}

/**
 * Standard toggler that accepts 1 (on) and 0 (off)
 * @param {*} value: boolean integer 0 for off or 1 for on
 * @returns React.Component
 */
const LightSwitch: FC<LightSwitchProps> = ({ value, name, toggle }, props) => {
  return (
    <ToggleButtonGroup type="checkbox">
      <ToggleButton
        name={name}
        checked={value === 1}
        color={value === 1 ? "success" : "secondary"}
        value={value}
        onClick={e => toggle(name, value === 1 ? 0 : 1) }
        {...props}
      >
        {value === 1 ? "On" : "Off"}
      </ToggleButton>
    </ToggleButtonGroup>
  )
}

export default LightSwitch
