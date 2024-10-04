import { Form } from "react-bootstrap"

const BotsActions = ({ defaultValue, handleChange }) => {
  return (
    <Form.Select
      aria-label="Select bulk actions"
      name="bulkActions"
      id="bulk-actions"
      onChange={handleChange}
      defaultValue={defaultValue}
    >
      <option value="">Select bulk action</option>
      <option value="delete-selected">Delete selected</option>
      <option value="unselect-all">Unselect all</option>
      <option value="completed">Show completed only</option>
      <option value="active">Show active only</option>
      <option value="select-all">Select all</option>
    </Form.Select>
  )
}

export default BotsActions
