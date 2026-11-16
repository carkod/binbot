import {
  Box,
  Button,
  Card,
  Menu,
  SimpleGrid,
  Table,
  Title,
  VisuallyHidden,
} from "@mantine/core";
import { type FC, useState } from "react";
import { useNavigate } from "react-router";
import {
  type User,
  useDeleteUserMutation,
  useGetUsersQuery,
} from "../../features/userApiSlice";
import ConfirmModal from "../components/ConfirmModal";
const UsersPage: FC = () => {
  const navigate = useNavigate();
  const { data: users = [], isFetching } = useGetUsersQuery(undefined, {
    refetchOnFocus: true,
  });
  const [deleteUser] = useDeleteUserMutation();
  const [userToDelete, setUserToDelete] = useState<User | null>(null);
  const confirmDelete = async (index: number) => {
    if (index === 1 && userToDelete) {
      await deleteUser(userToDelete.email).unwrap();
    }
    setUserToDelete(null);
  };
  return (
    <Box w="100%">
      <Card mb="md" mt={16}>
        <Box mb="sm">
          <SimpleGrid
            cols={2}
            style={{
              alignItems: "center",
            }}
          >
            <Title order={4}>User</Title>
            <Box ta="right">
              <Button onClick={() => navigate("/user/new")} type="button">
                Create User
              </Button>
            </Box>
          </SimpleGrid>
        </Box>
        <Box>
          <Box className="table-scroll">
            <Table highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Email</Table.Th>
                  <Table.Th>Role</Table.Th>
                  <Table.Th>Full name</Table.Th>
                  <Table.Th>Username</Table.Th>
                  <Table.Th>Description</Table.Th>
                  <Table.Th>Actions</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {users.map((user) => (
                  <Table.Tr key={user.email}>
                    <Table.Td>{user.email}</Table.Td>
                    <Table.Td>{user.role}</Table.Td>
                    <Table.Td>{user.full_name}</Table.Td>
                    <Table.Td>{user.username}</Table.Td>
                    <Table.Td>{user.description}</Table.Td>
                    <Table.Td>
                      <Menu>
                        <Menu.Target>
                          <Button
                            size="sm"
                            id={`user-actions-${user.email}`}
                            color="secondary"
                            type="button"
                          >
                            Actions
                          </Button>
                        </Menu.Target>
                        <Menu.Dropdown>
                          <Menu.Item
                            onClick={() =>
                              navigate(
                                `/user/edit?email=${encodeURIComponent(user.email)}`,
                              )
                            }
                          >
                            Edit
                          </Menu.Item>
                          <Menu.Item
                            onClick={() => setUserToDelete(user)}
                            c="danger.8"
                          >
                            Delete
                          </Menu.Item>
                        </Menu.Dropdown>
                      </Menu>
                    </Table.Td>
                  </Table.Tr>
                ))}
                {!isFetching && users.length === 0 && (
                  <Table.Tr>
                    <Table.Td colSpan={6} ta="center">
                      No users found
                    </Table.Td>
                  </Table.Tr>
                )}
                {isFetching && (
                  <Table.Tr>
                    <Table.Td colSpan={6} ta="center">
                      Loading users...
                    </Table.Td>
                  </Table.Tr>
                )}
              </Table.Tbody>
            </Table>
          </Box>
        </Box>
      </Card>
      <ConfirmModal
        show={Boolean(userToDelete)}
        onClose={() => setUserToDelete(null)}
        handleActions={confirmDelete}
        primary={
          <>
            <i className="fa-solid fa-trash" />
            <VisuallyHidden>Delete</VisuallyHidden>
          </>
        }
      >
        Are you sure you want to delete {userToDelete?.email}?
      </ConfirmModal>
    </Box>
  );
};
export default UsersPage;
