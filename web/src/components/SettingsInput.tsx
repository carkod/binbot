// @ts-nocheck
import React, { MouseEventHandler } from "react";
import { FormFeedback, FormGroup, Input, InputGroup, InputGroupText, Label } from "reactstrap";
import { checkValue } from "../validations";
import BotFormTooltip from "./BotFormTooltip";

const SettingsInput: React.FC<SettingsInputProps> = ({
  value,
  name,
  label,
  handleChange,
  handleBlur,
  errorMsg,
  infoText,
  unit,
  ...props
}) => {
  return (
    <FormGroup>
      {infoText ? 
        <BotFormTooltip name={name} text={infoText}>{label}</BotFormTooltip>
        :
        <Label for={name}>{label}</Label>
      }
      <InputGroup>
        <Input
          name={name}
          id={name}
          onChange={handleChange}
          onBlur={handleBlur}
          value={value}
          invalid={!checkValue(errorMsg)}
          {...props}
        />
        {unit && (
          <InputGroupText>{unit}</InputGroupText>
        )}
        {errorMsg && <FormFeedback>{errorMsg}</FormFeedback>}
        </InputGroup>
    </FormGroup>
  );
};

export default SettingsInput;

interface SettingsInputProps {
  value: HTMLElement;
  name: HTMLElement;
  handleChange: MouseEventHandler;
  handleBlur: MouseEventHandler;
  label?: HTMLElement;
  errorMsg: string;
  infoText: string;
  unit: string;
}
