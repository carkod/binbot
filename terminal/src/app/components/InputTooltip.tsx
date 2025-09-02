import React, { type FC } from "react";
import { Form, InputGroup, OverlayTrigger, Tooltip } from "react-bootstrap";
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
    <Form.Group>
      <OverlayTrigger
        placement="right"
        overlay={
          <Tooltip placement="top" className="in">
            {tooltip}
          </Tooltip>
        }
      >
        <Form.Label htmlFor={name}>
          {label}
          {required && <span className="u-required">*</span>}
        </Form.Label>
      </OverlayTrigger>
      <InputGroup>
        {children}
        {secondaryText && <InputGroup.Text>{secondaryText}</InputGroup.Text>}
      </InputGroup>
      {errors[name] && (
        <Form.Control.Feedback type="invalid">
          {errors[name]?.message}
        </Form.Control.Feedback>
      )}
    </Form.Group>
  );
};

export default InputTooltip;
