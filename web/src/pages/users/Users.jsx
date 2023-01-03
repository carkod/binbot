import moment from "moment";
import React from "react";
import { connect } from "react-redux";
import {
  Button,
  Card,
  CardBody,
  CardHeader,
  CardTitle,
  Col,
  Row,
} from "reactstrap";
import { getToken } from "../../request";
import { checkValue } from "../../validations";
import { getUsers, registerUser, editUser, deleteUser } from "./actions";
import UserForm from "./UserForm";

class Users extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      currentUser: props.currentUser,
    };
  }

  componentDidMount = () => {
    this.props.getUsers();
  };

  componentDidUpdate = (props, state) => {
    if (
      !checkValue(this.props.currentUser) &&
      props.currentUser !== this.props.currentUser
    ) {
      this.setState({
        currentUser: this.props.currentUser,
      });
    }
  };

  handleSubmit = (userData) => {
    if (checkValue(userData.id)) {
      this.props.registerUser(userData);
    } else {
      this.props.editUser(userData);
    }
  };

  editUser = (id) => {
    this.setState({
      currentUser: this.props.users.find((x) => x.id.$oid === id),
    });
  };

  deleteUser = (id) => {
    this.props.deleteUser(id);
  };

  render() {
    return (
      <>
        <div className="content">
          <Row>
            <Col md="5">
              <Card>
                <CardHeader>
                  <CardTitle tag="h4">Users list</CardTitle>
                </CardHeader>
                <CardBody>
                  <ul className="list-unstyled team-members">
                    {this.props.users &&
                      this.props.users.map((x, i) => (
                        <li key={x.id.$oid}>
                          <Row>
                            <Col>{x.email}</Col>
                            {!checkValue(x.last_login) && (
                              <Col>{moment(x.last_login.$date).fromNow()}</Col>
                            )}
                            <Col>{x.username}</Col>
                            <Col>
                              <Button
                                color="primary"
                                onClick={() => this.editUser(x.id.$oid)}
                              >
                                Edit
                              </Button>{" "}
                              <Button
                                color="primary"
                                onClick={() => this.deleteUser(x.id.$oid)}
                              >
                                Delete
                              </Button>
                            </Col>
                          </Row>
                        </li>
                      ))}
                  </ul>
                </CardBody>
              </Card>
            </Col>
            <Col md="7">
              <Card className="card-user">
                <CardHeader>
                  <CardTitle tag="h5">Edit user</CardTitle>
                </CardHeader>
                <CardBody>
                  {!checkValue(this.state.currentUser) && (
                    <UserForm
                      currentUser={this.state.currentUser}
                      handleSubmit={this.handleSubmit}
                    />
                  )}
                </CardBody>
              </Card>
            </Col>
          </Row>
          <Row>
            <Col md="12">
              <Card className="card-user">
                <CardHeader>
                  <CardTitle tag="h5">Register new user</CardTitle>
                </CardHeader>
                <CardBody>
                  <UserForm handleSubmit={this.handleSubmit} />
                </CardBody>
              </Card>
            </Col>
          </Row>
        </div>
      </>
    );
  }
}

const mapStateToProps = (s) => {
  const { users } = s.usersReducer;
  const token = getToken();
  let currentUser = null;
  if (users) {
    currentUser = users.find((x) => x.access_token === token);
  }

  return {
    users: users,
    currentUser: currentUser,
  };
};

export default connect(mapStateToProps, {
  getUsers,
  registerUser,
  editUser,
  deleteUser,
})(Users);
