import React, { useState } from "react";
import { Label, Tooltip } from "reactstrap";

const BotFormTooltip = ({ name, text, children }) => {
  const [tooltipOpen, setTooltipOpen] = useState(false);
  const toggle = () => setTooltipOpen(!tooltipOpen);

  return (
    <>
      <Label htmlFor={name}>
        <button type="button" className="btn--tooltip" id={`${name}-tooltip`}>
          {children}
        </button>
      </Label>
      <Tooltip isOpen={tooltipOpen} target={`${name}-tooltip`} toggle={toggle}>
        <small>{text}</small>
      </Tooltip>
    </>
  );
};

BotFormTooltip.argTypes = {
  placement: {
    control: { type: "select" },
    options: ["top", "left", "right", "bottom"],
  },
};

export default BotFormTooltip;
