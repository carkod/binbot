import { Typeahead } from "react-bootstrap-typeahead";
import Form from "react-bootstrap/Form";
import { checkValue } from "../validations.js";
import "react-bootstrap-typeahead/css/Typeahead.css";

export default function SymbolSearch({
  name,
  label,
  options,
  selected,
  handleChange,
  handleBlur,
  required = false,
  errorMsg = "",
}) {
  return (
    <>
      <Form.Group>
        <Form.Label>
          {label}
          {required && <span className="u-required">*</span>}
        </Form.Label>
        <Typeahead
          id={name}
          labelKey={name}
          onChange={handleChange}
          options={!checkValue(options) ? options : []}
          selected={selected ? [selected] : []}
          onBlur={handleBlur}
          className={errorMsg !== "" ? "is-invalid" : ""}
          isInvalid={errorMsg !== ""}
        />

        {errorMsg !== "" && (
          <Form.Control.Feedback type="invalid">
            {errorMsg}
          </Form.Control.Feedback>
        )}
      </Form.Group>
    </>
  );
}
