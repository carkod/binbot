import { Input, Stack, TextInput } from "@mantine/core";
import React, { type FC } from "react";
type SettingsInputProps = {
  value?: string | number;
  name?: string;
  label: string;
  handleChange?: (e: React.ChangeEvent<HTMLInputElement>) => void;
  handleBlur?: (e: FocusEvent) => void;
  errorMsg?: string;
  infoText?: string;
  type?: "text" | "number";
  step?: string | number;
  register?: any;
  required?: boolean;
};
const SettingsInput: FC<SettingsInputProps> = ({
  value,
  name,
  label,
  handleChange,
  handleBlur,
  errorMsg,
  infoText,
  register,
  type = "text",
  step,
  required = false,
}) => {
  const inputStep = step ?? (type === "number" ? "any" : undefined);
  return (
    <Stack gap={4} mb="sm">
      <Input.Label htmlFor={name}>{label}</Input.Label>
      <TextInput
        id={name}
        onChange={handleChange}
        onBlur={handleBlur}
        defaultValue={type === "number" ? String(value) : value}
        type={type}
        step={inputStep}
        {...register(name, { required: required })}
        error={!!errorMsg}
      />
      {errorMsg && <Input.Error>{errorMsg}</Input.Error>}
      {infoText && <Input.Description>{infoText}</Input.Description>}
    </Stack>
  );
};
export default SettingsInput;
