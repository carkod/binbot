import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { vi } from "vitest";
import { renderWithProviders } from "../../../utils/test-utils";
import { screen, waitFor } from "../../../utils/render";
import UserForm from "../UserForm";
import Users from "../Users";

const { createUser, deleteUser } = vi.hoisted(() => ({
  createUser: vi.fn(() => ({ unwrap: () => Promise.resolve() })),
  deleteUser: vi.fn(() => ({ unwrap: () => Promise.resolve() })),
}));

vi.mock("../../../features/userApiSlice", async () => ({
  ...(await vi.importActual("../../../features/userApiSlice")),
  useGetUsersQuery: () => ({
    data: [
      { email: "review@example.test", role: "user", full_name: "Review User" },
    ],
    isFetching: false,
  }),
  useDeleteUserMutation: () => [deleteUser],
  useRegisterUserMutation: () => [createUser, { isLoading: false }],
  useEditUserMutation: () => [vi.fn(), { isLoading: false }],
  useGetUserQuery: () => ({ data: undefined, isFetching: false }),
}));

function renderUsers() {
  return renderWithProviders(
    <MemoryRouter initialEntries={["/user"]}>
      <Routes>
        <Route path="/user" element={<Users />} />
        <Route path="/user/new" element={<UserForm mode="new" />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("user administration", () => {
  it("can reopen the same user's confirmation after cancelling and delete only on confirmation", async () => {
    const user = userEvent.setup();
    renderUsers();

    await user.click(screen.getByRole("button", { name: "Actions" }));
    await user.click(screen.getByRole("menuitem", { name: "Delete" }));
    expect(screen.getByRole("dialog")).toHaveTextContent("review@example.test");
    await user.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    expect(deleteUser).not.toHaveBeenCalled();

    await user.click(screen.getByRole("button", { name: "Actions" }));
    await user.click(screen.getByRole("menuitem", { name: "Delete" }));
    await user.click(screen.getByRole("button", { name: "Delete" }));
    expect(deleteUser).toHaveBeenCalledExactlyOnceWith("review@example.test");
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  });

  it("submits the selected role and active state when creating a user", async () => {
    const user = userEvent.setup();
    renderUsers();

    await user.click(screen.getByRole("button", { name: "Create User" }));
    await user.type(
      screen.getByRole("textbox", { name: "Email" }),
      "new@example.test",
    );
    await user.type(screen.getByLabelText("Password"), "test-password");
    await user.type(
      screen.getByRole("textbox", { name: "Full name" }),
      "New User",
    );
    await user.selectOptions(
      screen.getByRole("combobox", { name: "Role" }),
      "admin",
    );
    await user.click(screen.getByRole("switch", { name: /Active/ }));
    expect(screen.getByRole("switch", { name: /Active/ })).not.toBeChecked();
    await user.click(screen.getByRole("button", { name: "Create User" }));

    await waitFor(() =>
      expect(createUser).toHaveBeenCalledExactlyOnceWith({
        email: "new@example.test",
        password: "test-password",
        full_name: "New User",
        role: "admin",
        is_active: false,
        username: "",
        description: "",
      }),
    );
    expect(screen.getByRole("button", { name: "Actions" })).toBeVisible();
  });
});
