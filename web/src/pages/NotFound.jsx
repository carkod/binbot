import React, { Component } from "react";
import { Col, Row } from "reactstrap";

class NotFound extends Component {
  constructor(props) {
    super(props);
    this.state = {}
  }

  render() {
    return (
      <>
        <div className="content">
          <Row>
            <Col md="12">
              Page not found.
            </Col>
          </Row>
        </div>
      </>
    );
  }
}

export default NotFound;
