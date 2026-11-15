import { type ChangeEvent, useEffect, useState, type FC } from "react";
import { Typeahead } from "react-bootstrap-typeahead";
import "react-bootstrap-typeahead/css/Typeahead.css";
import Form from "react-bootstrap/Form";
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

const SymbolSearch: FC<SymbolSearchProps> = ({
  name,
  label = null,
  value,
  onBlur = () => undefined,
  required = false,
  disabled = false,
  errors = {},
  placeholder = "",
  options: providedOptions,
  size,
  onChange,
  onInputChange,
}) => {
  const [state, setState] = useState<string>(value ?? "");
  const [options, setOptions] = useState<string[]>([]);
  const { symbolsList } = useSymbolData();
  const availableOptions = providedOptions ?? symbolsList;

  useEffect(() => {
    if (value !== undefined) {
      setState(value);
    }
  }, [value]);

  useEffect(() => {
    if (availableOptions.length > 0) {
      setOptions(availableOptions);
    }
  }, [availableOptions]);

  return (
    <Form.Group>
      {label && (
        <Form.Label htmlFor={name}>
          {label}
          {required && <span className="u-required">*</span>}
        </Form.Label>
      )}
      <Typeahead
        id={name}
        size={size}
        inputProps={{ id: name, name, required }}
        options={options}
        {...(required
          ? { isInvalid: Boolean(errors?.[name]) || !state.trim() }
          : {})}
        disabled={disabled}
        selected={state ? [state] : []}
        onChange={(selected) => {
          // Typeahead also emits an empty selection while the user types.
          // Input changes already update the text through onInputChange.
          if (selected.length > 0) {
            const symbol = selected[0] as string;
            setState(symbol);
            onChange?.(symbol);
          }
        }}
        onInputChange={(value) => {
          setState(value);
          onInputChange?.(value);
        }}
        onBlur={(e) => onBlur(e)}
        placeholder={placeholder}
      />

      {errors[name] && (
        <Form.Control.Feedback type="invalid" className="d-block" role="alert">
          {errors[name]}
        </Form.Control.Feedback>
      )}
    </Form.Group>
  );
};

export default SymbolSearch;
