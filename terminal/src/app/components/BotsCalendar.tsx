import { DatePickerInput } from "@mantine/dates";
import { type FC } from "react";
import { convertTsToInputDate } from "../../utils/time";

interface BotsDateFilterProps {
  selectedDate: number | undefined;
  title: string;
  controlId: string; // Unique ID to identify
  handleDateChange: (ts: number | undefined) => void;
}

const BotsDateFilter: FC<BotsDateFilterProps> = ({
  title,
  selectedDate,
  controlId,
  handleDateChange,
}) => {
  return (
    <DatePickerInput
      id={controlId}
      label={title}
      placeholder="Select date"
      value={selectedDate ? convertTsToInputDate(selectedDate) : null}
      valueFormat="DD/MM/YYYY"
      onChange={(date) =>
        handleDateChange(date ? new Date(date).getTime() : undefined)
      }
      clearable
      clearButtonProps={{ "aria-label": `Clear ${title.toLowerCase()}` }}
      mb="sm"
    />
  );
};

export default BotsDateFilter;
