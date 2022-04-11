import React from "react";
import { FormFeedback, FormGroup, Input, Label } from "reactstrap";
import { checkValue } from "../validations";

const SettingsInput = ({
  value,
  name,
  label,
  handleChange,
  handleBlur,
  errorMsg,
  ...props
}) => {
  return (
    <FormGroup>
      <Label for={name}>{label}</Label>
      <Input
        type="input"
        name={name}
        id={name}
        onChange={handleChange}
        onBlur={handleBlur}
        defaultValue={value}
        invalid={!checkValue(errorMsg)}
        {...props}
      />
      {errorMsg && <FormFeedback>{errorMsg}</FormFeedback>}
    </FormGroup>
  );
};

export default SettingsInput;
