import React, { Component } from "react";
// reactstrap components
import { Col, Row } from "reactstrap";
import RegistrationForm from "../../components/RegistrationForm";
import { connect } from "react-redux";
import { registerUser } from "./actions";

class Registration extends Component {
  handleSubmit = (data) => {
    this.props.registerUser(data);
  };

  render() {
    return (
      <>
        <div className="content">
          <Row>
            <Col md="12">
              <RegistrationForm onSubmit={this.handleSubmit} />
            </Col>
          </Row>
        </div>
      </>
    );
  }
}

export default connect(null, { registerUser })(Registration);
