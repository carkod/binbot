import { Switch } from "@mantine/core";
import type { FieldValues, UseFormRegister } from "react-hook-form";
export type LightSwitchProps = {
  value: boolean;
  name: string;
  toggle?: (name: string, value: boolean) => void;
  register?: UseFormRegister<FieldValues>;
  required?: boolean;
};
const LightSwitch = ({
  value,
  name,
  toggle,
  register,
  required = false,
}: LightSwitchProps) => {
  const field = register?.(name, { required });
  return (
    <Switch
      {...field}
      id={name}
      name={name}
      checked={value}
      label={value ? "On" : "Off"}
      color="success"
      onChange={(event) => {
        field?.onChange(event);
        toggle?.(name, value);
      }}
    />
  );
};
export default LightSwitch;
