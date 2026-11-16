import { Autocomplete } from "@mantine/core";
import type { ChangeEvent } from "react";
import { useEffect, useState } from "react";
import { useSymbolData } from "../hooks";

type SymbolSearchProps = {
  name: string;
  label?: string;
  value?: string;
  defaultValue?: string;
  required?: boolean;
  disabled?: boolean;
  placeholder?: string;
  options?: string[];
  size?: "sm" | "lg";
  onChange?: (symbol: string) => void;
  onInputChange?: (symbol: string) => void;
  onBlur?: (e: ChangeEvent<HTMLInputElement>) => void;
  errors?: object;
};

const SymbolSearch = ({
  name,
  label,
  value,
  defaultValue = "",
  onBlur,
  required = false,
  disabled = false,
  errors = {},
  placeholder = "",
  options,
  size,
  onChange,
  onInputChange,
}: SymbolSearchProps) => {
  const [text, setText] = useState(value ?? defaultValue);

  const { symbolsList } = useSymbolData();

  useEffect(() => {
    if (value !== undefined) setText(value);
  }, [value]);

  const error = errors[name];

  return (
    <Autocomplete
      id={name}
      name={name}
      label={label}
      required={required}
      disabled={disabled}
      placeholder={placeholder}
      size={size}
      data={options ?? symbolsList}
      value={text}
      limit={50}
      error={error ? String(error.message ?? error) : required && !text.trim()}
      onChange={(next) => {
        setText(next);
        onInputChange?.(next);
      }}
      onOptionSubmit={(next) => {
        setText(next);
        onChange?.(next);
      }}
      onBlur={onBlur}
      comboboxProps={{ withinPortal: true }}
    />
  );
};

export default SymbolSearch;
