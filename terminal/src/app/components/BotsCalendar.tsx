import { useState, type FC } from "react";
import { Form } from "react-bootstrap";
import { convertTsToInputDate } from "../../utils/time";

interface BotsDateFilterProps {
  selectedDate: number;
  title: string;
  controlId: string; // Unique ID to identify
  handleDateChange: (ts: number) => void;
}

const BotsDateFilter: FC<BotsDateFilterProps> = ({
  title,
  selectedDate,
  controlId,
  handleDateChange,
}) => {
  const defaultDate: string = selectedDate
    ? convertTsToInputDate(selectedDate)
    : "";
  const [date, setDate] = useState(defaultDate);

  return (
    <Form.Group controlId={controlId}>
      <Form.Label>{title}</Form.Label>
      <Form.Control
        type="date"
        value={date}
        onChange={(e) => setDate(e.target.value)}
        onBlur={(e) => {
          const ts: number = new Date(e.target.value).getTime();
          handleDateChange(ts);
        }}
      />
    </Form.Group>
  );
};

export default BotsDateFilter;
