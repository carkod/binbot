import { type FC } from "react";
import { Form } from "react-bootstrap";

export enum BulkAction {
  NONE = "",
  DELETE = "delete-selected",
  UNSELECT_ALL = "unselect-all",
  COMPLETED = "completed",
  ACTIVE = "active",
  SELECT_ALL = "select-all",
}
interface BotsActionsProps {
  defaultValue: string;
  handleChange: (e: React.ChangeEvent<HTMLSelectElement>) => void;
}

const BotsActions: FC<BotsActionsProps> = ({ defaultValue, handleChange }) => {
  return (
    <Form.Group>
      <Form.Select
        aria-label="Select bulk actions"
        name="bulkActions"
        id="bulk-actions"
        onChange={handleChange}
        defaultValue={defaultValue}
      >
        <option value="">Select bulk action</option>
        <option value={BulkAction.DELETE}>Delete selected</option>
        <option value={BulkAction.UNSELECT_ALL}>Unselect all</option>
        <option value={BulkAction.COMPLETED}>Show completed only</option>
        <option value={BulkAction.ACTIVE}>Show active only</option>
        <option value={BulkAction.SELECT_ALL}>Select all</option>
      </Form.Select>
    </Form.Group>
  );
};

export default BotsActions;
