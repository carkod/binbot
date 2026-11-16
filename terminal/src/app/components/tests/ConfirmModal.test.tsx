import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { vi } from "vitest";
import { render, screen, waitFor } from "../../../utils/render";
import ConfirmModal from "../ConfirmModal";

describe("confirmation dialog", () => {
  it.each(["Escape", "Cancel"])(
    "can reopen after cancelling with %s",
    async (method) => {
      const user = userEvent.setup();
      const handleActions = vi.fn();
      function Confirmation() {
        const [show, setShow] = useState(false);
        return (
          <>
            <button onClick={() => setShow(true)}>Delete record</button>
            <ConfirmModal
              show={show}
              onClose={() => setShow(false)}
              handleActions={handleActions}
              primary="Delete"
            >
              Confirm deletion
            </ConfirmModal>
          </>
        );
      }
      render(<Confirmation />);

      await user.click(screen.getByRole("button", { name: "Delete record" }));
      expect(
        screen.getByRole("dialog", { name: "Are you sure?" }),
      ).toBeVisible();
      if (method === "Escape") await user.keyboard("{Escape}");
      else await user.click(screen.getByRole("button", { name: "Cancel" }));
      await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
      expect(handleActions).not.toHaveBeenCalled();
      await user.click(screen.getByRole("button", { name: "Delete record" }));
      expect(
        screen.getByRole("dialog", { name: "Are you sure?" }),
      ).toBeVisible();
      await user.click(screen.getByRole("button", { name: /^Delete$/ }));
      expect(handleActions).toHaveBeenCalledExactlyOnceWith(1);
    },
  );

  it("keeps primary and secondary action identifiers distinct", async () => {
    const user = userEvent.setup();
    const handleActions = vi.fn();
    render(
      <ConfirmModal
        show
        onClose={vi.fn()}
        handleActions={handleActions}
        primary="Delete"
        secondary="Archive"
      />,
    );

    await user.click(screen.getByRole("button", { name: "Archive" }));
    expect(handleActions).toHaveBeenLastCalledWith(2);
    await user.click(screen.getByRole("button", { name: "Delete" }));
    expect(handleActions).toHaveBeenLastCalledWith(1);
  });
});
