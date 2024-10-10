import { useEffect, useState, type FC } from "react"
import { Typeahead } from "react-bootstrap-typeahead"
import "react-bootstrap-typeahead/css/Typeahead.css"
import Form from "react-bootstrap/Form"
import { useForm, type FieldErrors } from "react-hook-form"
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
  selected?: Option[]
  onBlur?: (e: React.FocusEvent<HTMLInputElement>) => void
}> = (
  {
    name,
    label,
    options,
    selected,
    errors = null,
    required = false,
    disabled = false,
  }
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
          isInvalid={!!errors?.[name] || selected === ""}
          disabled={disabled}
          selected={selected ? [selected] : []}
        />

        {/* {errors[name] && (
          <Form.Control.Feedback type="invalid">
            {errors[name as keyof FieldErrors].message}
          </Form.Control.Feedback>
        )} */}
      </Form.Group>
    </>
  )
}

export default SymbolSearch
