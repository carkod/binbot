import React, { type FC } from "react";
import { Form, InputGroup } from "react-bootstrap";
import { type FieldErrors } from "react-hook-form";
import { type Bot } from "../../features/bots/botInitialState";

interface InputTooltipProps {
  name: string;
  tooltip: string;
  children: React.ReactNode;
  label: string;
  errors?: FieldErrors<Bot>;
  required?: boolean;
  secondaryText?: string;
}

export const InputTooltip: FC<InputTooltipProps> = ({
  name,
  tooltip,
  label,
  children,
  errors,
  required = false,
  secondaryText = undefined,
}) => {
  return (
    <Form.Group className="position-relative">
      <Form.Label htmlFor={name}>
        {label}
        {required && <span className="u-required">*</span>}
      </Form.Label>
      <InputGroup>
        {children}
        {secondaryText && <InputGroup.Text>{secondaryText}</InputGroup.Text>}
      </InputGroup>
      <Form.Control.Feedback tooltip>
        <small>{tooltip}</small>
      </Form.Control.Feedback>
      {errors[name] && (
        <Form.Control.Feedback type="invalid">
          {errors[name]}
        </Form.Control.Feedback>
      )}
    </Form.Group>
  );
};

export default InputTooltip;
