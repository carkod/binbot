import Form from "react-bootstrap/Form"
import { Typeahead } from "react-bootstrap-typeahead"
import "react-bootstrap-typeahead/css/Typeahead.css"
import { useEffect, useState, type FC } from "react"
import { type FieldErrors } from "react-hook-form"
import { type Bot } from "../../features/bots/botInitialState"
import { type Option } from "react-bootstrap-typeahead/types/types"

const SymbolSearch: FC<{
  name: string
  label: string
  options: string[]
  selected: string
  handleChange: (selected: Option[]) => void
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

  const [ data, setData ] = useState([])

  useEffect(() => {
    if (options && options.length > 0) {
      setData(options)
    }
  }, [options, setData])

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
          options={data}
          selected={selected ? [selected] : []}
          onBlur={handleBlur}
          className={errors?.[name] || selected === "" ? "is-invalid" : ""}
          isInvalid={!!errors?.[name] || selected === ""}
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
