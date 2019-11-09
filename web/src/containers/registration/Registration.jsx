import React, { Component } from "react";
// reactstrap components
import { Col, Row } from "reactstrap";
import RegistrationForm from '../../components/RegistrationForm';
import { connect } from "react-redux";
import { registerUser } from './actions';
// const data = {
//   userBgImg: 'https://picsum.photos/1440/900?random=1',
//   userProfileImg: 'https://picsum.photos/300/300?random=1',
//   username: 'carkod',
//   userQuote: 'I like the way you work it'
// }

class Registration extends Component {

  handleSubmit = (data) => {
    this.props.registerUser(data);
  }

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
