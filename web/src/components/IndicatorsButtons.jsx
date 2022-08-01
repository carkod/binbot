import { ToggleButton, ToggleButtonGroup } from "react-bootstrap";

const IndicatorsButtons = ({toggle, handleChange}) => {
  return (
    <ToggleButtonGroup type="checkbox">
      <ToggleButton
        id={`toggle-indicator`}
        name="toggle-indicator"
        checked={toggle}
        onChange={() => handleChange(!toggle)}
      >
        Indicators {toggle ? "on" : "off"}
      </ToggleButton>
    </ToggleButtonGroup>
  );
};

export default IndicatorsButtons;