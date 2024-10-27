import { type FC } from "react";
import { Col, Row } from "react-bootstrap";

const NotFound: FC = () => {
  return (
    <div className="content">
      <Row>
        <Col md="12">Page not found.</Col>
      </Row>
    </div>
  );
};

export default NotFound;
