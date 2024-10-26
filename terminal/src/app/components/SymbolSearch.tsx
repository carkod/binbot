import { useEffect, useState, type FC } from "react";
import { Typeahead } from "react-bootstrap-typeahead";
import "react-bootstrap-typeahead/css/Typeahead.css";
import Form from "react-bootstrap/Form";
import { useGetSettingsQuery } from "../../features/autotradeApiSlice";

// Filter by base asset (balance_to_use) provided by autotrade settings
// This is done in the front-end because it doesn't matter in the back-end, we always get the full list of symbols
export const filterSymbolByBaseAsset = (options: string[], baseAsset: string): string[] => {
  return options.filter((item) => item.endsWith(baseAsset));
}

const SymbolSearch: FC<{
  name: string;
  label: string;
  options: string[];
  value?: string;
  defaultValue?: string;
  required?: boolean;
  disabled?: boolean;
  onBlur?: (e: React.FocusEvent<HTMLInputElement>) => void;
  errors?: object;
}> = ({
  name,
  label,
  options,
  value,
  onBlur,
  required = false,
  disabled = false,
  errors = {}
}) => {
  const [state, setState] = useState<string>(value);
  const [optionsState, setOptionsState] = useState<string[]>(options);
  const { data: autotradeSettings } = useGetSettingsQuery();

  useEffect(() => {
    if (value) {
      setState(value);
    }
    // BTCUSDT, BTCUSDC, BTCETH, ETHUSDT, ETHUSDC -> BTCUSDC
    // check test for examples
    if (options && options.length > 0 ) {
      let updatedOptions = options;
      if (autotradeSettings?.balance_to_use) {
        updatedOptions = filterSymbolByBaseAsset(options, autotradeSettings.balance_to_use);
      }
      setOptionsState(updatedOptions);
    }
  }, [value, options, autotradeSettings?.balance_to_use]);

  return (
    <Form.Group>
      <Form.Label>
        {label}
        {required && <span className="u-required">*</span>}
      </Form.Label>
      <Typeahead
        id={name}
        options={optionsState}
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
