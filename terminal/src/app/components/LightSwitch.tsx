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
const LightSwitch: FC<LightSwitchProps> = ({
  value,
  name,
  toggle,
  register,
  required = false,
}) => {
  return (
    <ToggleButtonGroup type="checkbox">
      <ToggleButton
        type="checkbox"
        id={name}
        name={name}
        value={name}
        checked={value}
        variant={value ? "success" : "secondary"}
        onClick={() => toggle?.(name, value)}
        {...register?.(name, { required })}
      >
        {value ? "On" : "Off"}
      </ToggleButton>
    </ToggleButtonGroup>
  );
};

export default LightSwitch;
