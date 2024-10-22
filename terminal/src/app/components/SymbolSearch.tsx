import { useEffect, useState, type FC } from "react";
import { Typeahead } from "react-bootstrap-typeahead";
import "react-bootstrap-typeahead/css/Typeahead.css";
import Form from "react-bootstrap/Form";

const SymbolSearch: FC<{
  name: string;
  label: string;
  options: string[];
  value?: string;
  defaultValue?: string;
  required?: boolean;
  disabled?: boolean;
  onBlur?: (e: React.FocusEvent<HTMLInputElement>) => void;
  onChange?: (selected: string) => void;
  errors?: object;
}> = ({
  name,
  label,
  options,
  value,
  onChange,
  onBlur,
  required = false,
  disabled = false,
  errors = {},
}) => {
  const [state, setState] = useState<string>(value);

  useEffect(() => {
    if (value) {
      setState(value);
    }
  }, [value]);

  return (
    <Form.Group>
      <Form.Label>
        {label}
        {required && <span className="u-required">*</span>}
      </Form.Label>
      <Typeahead
        id={name}
        options={options}
        isInvalid={Boolean(errors?.[name]) || Boolean(value) === false}
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
