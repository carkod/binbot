import { type FC } from "react";
import { ToggleButton, ToggleButtonGroup } from "react-bootstrap";
import { type UseFormRegister, type FieldValues } from "react-hook-form";

export type LightSwitchProps = {
  value: boolean;
  name: string;
  toggle?: (name: string, value: boolean) => void;
  register?: UseFormRegister<FieldValues>;
  required?: boolean;
};

/**
 * Standard toggler that accepts boolean
 * @param {*} value: boolean
 * @returns React.Component
 */
const LightSwitch: FC<LightSwitchProps> = (
  { value, name, toggle, register, required = false },
  props,
) => {
  return (
    <ToggleButtonGroup type="checkbox">
      <ToggleButton
        name={name}
        checked={value}
        color={value ? "success" : "secondary"}
        defaultValue={value}
        onClick={(e) => toggle(name, value)}
        {...register(name, { required: required })}
        {...props}
      >
        {value ? "On" : "Off"}
      </ToggleButton>
    </ToggleButtonGroup>
  );
};

export default LightSwitch;
