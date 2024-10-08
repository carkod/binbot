import Form from "react-bootstrap/Form"
import { Typeahead } from "react-bootstrap-typeahead"
import "react-bootstrap-typeahead/css/Typeahead.css"
import { type FC } from "react"
import { type FieldErrors } from "react-hook-form"
import { type Bot } from "../../features/bots/botInitialState"

const SymbolSearch: FC<{
  name: string
  label: string
  options: string[]
  selected: string
  handleChange: (selected: string[]) => void
  handleBlur: () => void
  required?: boolean
  errors?: FieldErrors<Bot>
  disabled?: boolean
}> = (
  {
    name,
    label,
    options,
    selected,
    handleChange,
    handleBlur,
    errors,
    required = false,
    disabled = false,
  },
  ...props
) => {
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
          options={options ? options : []}
          selected={selected ? [selected] : []}
          onBlur={handleBlur}
          className={errors ? "is-invalid" : ""}
          isInvalid={!!errors}
          disabled={disabled}
          {...props}
        />

        {errors[name] && (
          <Form.Control.Feedback type="invalid">
            {errors[name as keyof FieldErrors].message}
          </Form.Control.Feedback>
        )}
      </Form.Group>
    </>
  )
}

export default SymbolSearch
