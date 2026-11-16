import { NativeSelect, Stack } from "@mantine/core";
import type { ChangeEvent, FC } from "react";
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
  handleChange: (e: ChangeEvent<HTMLSelectElement>) => void;
}
const BotsActions: FC<BotsActionsProps> = ({ defaultValue, handleChange }) => {
  return (
    <Stack gap={4} mb="sm">
      <NativeSelect
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
      </NativeSelect>
    </Stack>
  );
};
export default BotsActions;
