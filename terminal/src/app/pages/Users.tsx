import { type FC, useState } from "react";
import {
  Button,
  Card,
  Col,
  Container,
  Dropdown,
  Row,
  Table,
} from "react-bootstrap";
import { useNavigate } from "react-router-dom";
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
    <Container fluid>
      <Card className="mt-3">
        <Card.Header>
          <Row className="align-items-center">
            <Col>
              <Card.Title>User</Card.Title>
            </Col>
            <Col className="text-end">
              <Button onClick={() => navigate("/user/new")}>Create User</Button>
            </Col>
          </Row>
        </Card.Header>
        <Card.Body>
          <Table responsive hover>
            <thead>
              <tr>
                <th>Email</th>
                <th>Role</th>
                <th>Full name</th>
                <th>Username</th>
                <th>Description</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map((user) => (
                <tr key={user.email}>
                  <td>{user.email}</td>
                  <td>{user.role}</td>
                  <td>{user.full_name}</td>
                  <td>{user.username}</td>
                  <td>{user.description}</td>
                  <td>
                    <Dropdown>
                      <Dropdown.Toggle
                        size="sm"
                        variant="secondary"
                        id={`user-actions-${user.email}`}
                      >
                        Actions
                      </Dropdown.Toggle>
                      <Dropdown.Menu>
                        <Dropdown.Item
                          onClick={() =>
                            navigate(
                              `/user/edit?email=${encodeURIComponent(user.email)}`,
                            )
                          }
                        >
                          Edit
                        </Dropdown.Item>
                        <Dropdown.Item
                          className="text-danger"
                          onClick={() => setUserToDelete(user)}
                        >
                          Delete
                        </Dropdown.Item>
                      </Dropdown.Menu>
                    </Dropdown>
                  </td>
                </tr>
              ))}
              {!isFetching && users.length === 0 && (
                <tr>
                  <td colSpan={6} className="text-center">
                    No users found
                  </td>
                </tr>
              )}
              {isFetching && (
                <tr>
                  <td colSpan={6} className="text-center">
                    Loading users...
                  </td>
                </tr>
              )}
            </tbody>
          </Table>
        </Card.Body>
      </Card>
      <ConfirmModal
        show={Boolean(userToDelete)}
        handleActions={confirmDelete}
        primary={
          <>
            <i className="fa-solid fa-trash" />
            <span className="visually-hidden">Delete</span>
          </>
        }
      >
        Are you sure you want to delete {userToDelete?.email}?
      </ConfirmModal>
    </Container>
  );
};

export default UsersPage;
