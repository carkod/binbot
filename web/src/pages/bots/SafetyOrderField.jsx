import { Col, FormFeedback, Input, Label, Row } from "reactstrap";

export default function SafetyOrderField({id, price_deviation_so, priceDevSoError, so_size, soSizeError, handleChange, handleBlur }) {
  return (
    <Row className="u-margin-bottom">
      <Col md="6" sm="12">
        <Label htmlFor="price_deviation_so">Price deviation (%)</Label>
        <Input
          invalid={priceDevSoError}
          type="text"
          name="price_deviation_so"
          id="price_deviation_so"
          onChange={handleChange(id)}
          onBlur={handleBlur}
          value={price_deviation_so}
        />
        <FormFeedback>
          <strong>Price deviation</strong> is required.
        </FormFeedback>
        <small>
          How much does the price have to drop to create a Safety Order?
        </small>
      </Col>
      <Col md="6" sm="12">
        <Label for="so_size">Safety order size</Label>
        <Input
          invalid={soSizeError}
          type="text"
          name="so_size"
          id="so_size"
          onChange={handleChange(id)}
          onBlur={handleBlur}
          value={so_size}
        />
        <FormFeedback>
          <strong>Safety order size</strong> is required.
        </FormFeedback>
      </Col>
    </Row>
  );
}
