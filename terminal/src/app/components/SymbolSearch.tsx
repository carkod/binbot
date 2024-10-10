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
  defaultSelected?: string
  required?: boolean
  errors?: FieldErrors<Bot>
  disabled?: boolean
  onChange?: (selected: string[]) => void
}> = (
  {
    name,
    label,
    options,
    defaultSelected,
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
          options={data}
          defaultSelected={defaultSelected ? [defaultSelected] : []}
          isInvalid={!!errors?.[name] || defaultSelected === ""}
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
