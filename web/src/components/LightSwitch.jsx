import React from "react";
import PropTypes from "prop-types";
import { Button } from "reactstrap";

/**
 * Standard toggler that accepts 1 (on) and 0 (off)
 * @param {*} value: boolean integer 0 for off or 1 for on
 * @returns React.Component
 */
const LightSwitch = ({ value, name, toggle }, props) => {
  return (
    <Button
      name={name}
      color={value === 1 ? "success" : "secondary"}
      onClick={(e) => toggle(name, value)}
      {...props}
    >
      {value === 1 ? "On" : "Off"}
    </Button>
  );
};

LightSwitch.propTypes = {
  value: PropTypes.oneOf([0, 1]),
  name: PropTypes.string,
  toggle: PropTypes.func,
};

export default LightSwitch;
