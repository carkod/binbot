import React, { type ChangeEvent, useEffect, useState, type FC } from "react";
import { Typeahead } from "react-bootstrap-typeahead";
import "react-bootstrap-typeahead/css/Typeahead.css";
import Form from "react-bootstrap/Form";
import { useGetSettingsQuery } from "../../features/autotradeApiSlice";

type SymbolSearchProps = {
  name: string;
  label?: string;
  options: string[];
  value?: string;
  defaultValue?: string;
  required?: boolean;
  disabled?: boolean;
  placeholder?: string;
  onBlur?: (e: ChangeEvent<HTMLInputElement>) => void;
  errors?: object;
};

const SymbolSearch: FC<SymbolSearchProps> = ({
  name,
  label = null,
  options,
  value,
  onBlur,
  required = false,
  disabled = false,
  errors = {},
  placeholder = "",
}) => {
  const [state, setState] = useState<string>(value);
  const [optionsState, setOptionsState] = useState<string[]>(options);
  const { data: autotradeSettings } = useGetSettingsQuery();

  useEffect(() => {
    if (value) {
      setState(value);
    }
    if (options && options.length > 0) {
      setOptionsState(options);
    }
  }, [value, options, autotradeSettings?.fiat]);

  return (
    <Form.Group>
      {label && (
        <Form.Label>
          {label}
          {required && <span className="u-required">*</span>}
        </Form.Label>
      )}
      <Typeahead
        id={name}
        options={optionsState}
        {...(required
          ? { isInvalid: Boolean(errors?.[name]) || Boolean(value) === false }
          : {})}
        disabled={disabled}
        selected={state ? [state] : []}
        onChange={(selected) => {
          if (selected.length > 0) {
            setState(selected[0] as string);
          }
        }}
        onInputChange={(value) => {
          setState(value);
        }}
        onBlur={(e) => onBlur(e)}
        placeholder={placeholder}
      />

      {errors[name] && (
        <Form.Control.Feedback type="invalid">
          {errors[name]}
        </Form.Control.Feedback>
      )}
    </Form.Group>
  );
};

export default SymbolSearch;
