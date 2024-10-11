import { useEffect, useState, type FC } from "react"
import { Typeahead } from "react-bootstrap-typeahead"
import "react-bootstrap-typeahead/css/Typeahead.css"
import { type Option } from "react-bootstrap-typeahead/types/types"
import Form from "react-bootstrap/Form"
import { FieldErrors, useForm } from "react-hook-form"

const SymbolSearch: FC<{
  name: string
  label: string
  options: string[]
  value?: string
  required?: boolean
  disabled?: boolean
  selected?: string
  onBlur?: (e: React.FocusEvent<HTMLInputElement>) => void
  onChange?: (selected: Option[]) => void
  errors?: object
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

  const [selectedValue, setSelectedValue] = useState<string | undefined>(value)

  useEffect(() => {
    if (value) {
      setSelectedValue(value)
    }
  }, [value])

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
          options={options}
          isInvalid={errors?.[name] || Boolean(selectedValue) === false}
          disabled={disabled}
          selected={selectedValue ? [selectedValue] : []}
          onChange={selected => onChange(selected)}
          onBlur={e => onBlur(e)}
        />

        {errors[name] && (
          <Form.Control.Feedback type="invalid">
            {errors[name].message}
          </Form.Control.Feedback>
        )}
      </Form.Group>
    </>
  )
}

export default SymbolSearch
