import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { vi } from "vitest";
import { render, screen } from "../../../utils/render";
import BotsDateFilter from "../BotsCalendar";

it("applies a calendar selection immediately and clears the date filter", async () => {
  const user = userEvent.setup();

  const onDateChange = vi.fn();

  function Filter() {
    const [selectedDate, setSelectedDate] = useState<number | undefined>(
      new Date(2026, 10, 9).getTime(),
    );

    return (
      <BotsDateFilter
        controlId="startDate"
        title="Start date"
        selectedDate={selectedDate}
        handleDateChange={(value) => {
          setSelectedDate(value);
          onDateChange(value);
        }}
      />
    );
  }

  render(<Filter />);

  const picker = screen.getByRole("button", { name: /^Start date/ });

  await user.click(picker);
  await user.click(screen.getByRole("button", { name: "10 November 2026" }));
  expect(onDateChange).toHaveBeenLastCalledWith(Date.UTC(2026, 10, 10));
  expect(picker).toHaveTextContent("10/11/2026");
  await user.click(screen.getByRole("button", { name: "Clear start date" }));
  expect(onDateChange).toHaveBeenLastCalledWith(undefined);
  expect(picker).toHaveTextContent("Select date");
});

it("reflects dates changed or reset by its parent", () => {
  const props = {
    controlId: "endDate",
    title: "End date",
    handleDateChange: vi.fn(),
  };

  const { rerender } = render(
    <BotsDateFilter
      {...props}
      selectedDate={new Date(2026, 10, 12).getTime()}
    />,
  );

  const picker = screen.getByRole("button", { name: /^End date/ });

  expect(picker).toHaveTextContent("12/11/2026");
  rerender(
    <BotsDateFilter
      {...props}
      selectedDate={new Date(2026, 10, 16).getTime()}
    />,
  );
  expect(picker).toHaveTextContent("16/11/2026");
  rerender(<BotsDateFilter {...props} selectedDate={undefined} />);
  expect(picker).toHaveTextContent("Select date");
});
