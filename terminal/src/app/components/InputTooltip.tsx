import { Group, Input, Stack, Tooltip } from "@mantine/core";
import type { ReactNode } from "react";
import type { FieldErrors } from "react-hook-form";
import type { Bot } from "../../features/bots/botInitialState";

interface InputTooltipProps {
  name: string;
  tooltip: string;
  children: ReactNode;
  label: string;
  errors?: FieldErrors<Bot>;
  required?: boolean;
  secondaryText?: string;
}

export const InputTooltip = ({
  name,
  tooltip,
  label,
  children,
  errors = {},
  required = false,
  secondaryText,
}: InputTooltipProps) => (
  <Stack gap={4} w="100%" style={{ minWidth: 0 }}>
    <Tooltip label={tooltip} multiline maw={320} withArrow>
      <Input.Label htmlFor={name} required={required}>
        {label}
      </Input.Label>
    </Tooltip>
    <Group gap="xs" wrap="nowrap" className="field-row">
      {children}
      {secondaryText && <Input.Description>{secondaryText}</Input.Description>}
    </Group>
    {errors[name] && (
      <Input.Error>
        {String(errors[name]?.message ?? "Invalid value")}
      </Input.Error>
    )}
  </Stack>
);

export default InputTooltip;
