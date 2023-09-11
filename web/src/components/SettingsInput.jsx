import React from "react";
import { FormFeedback, FormGroup, Input, Label } from "reactstrap";
import { checkValue } from "../validations";
import BotFormTooltip from "./BotFormTooltip";

const SettingsInput = ({
  value,
  name,
  label,
  handleChange,
  handleBlur,
  errorMsg,
  infoText,
  ...props
}) => {
  return (
    <FormGroup>
      {infoText ? 
        <BotFormTooltip name={name} text={infoText}>{label}</BotFormTooltip>
        :
        <Label for={name}>{label}</Label>
      }
      <Input
        name={name}
        id={name}
        onChange={handleChange}
        onBlur={handleBlur}
        value={value}
        invalid={!checkValue(errorMsg)}
        {...props}
      />
      {errorMsg && <FormFeedback>{errorMsg}</FormFeedback>}
    </FormGroup>
  );
};

export default SettingsInput;
