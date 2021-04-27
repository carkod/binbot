import {
  Col,
  FormFeedback,
  Input,
  InputGroup,
  InputGroupAddon,
  InputGroupText,
  Label,
  Row,
  TabPane,
} from "reactstrap";

export default function ShortTab({
  state,
  handleChange,
  handleBlur,
  handleShortOrder,
}) {
  return (
    <TabPane tabId="short">
      <Row className="u-margin-bottom">
        <Col md="6" sm="12">
          <Label htmlFor="short_stop_price">Short order stop</Label>
          <InputGroup>
            <Input
              type="number"
              name="short_stop_price"
              onChange={handleShortOrder}
              onBlur={handleBlur}
              value={state.short_stop_price}
            />
            <InputGroupAddon addonType="append">
              <InputGroupText>%</InputGroupText>
            </InputGroupAddon>
          </InputGroup>
          <small>Price</small>
        </Col>
        <Col md="6" sm="12">
          <Label htmlFor="short_order">Short order</Label>
          <Input
            type="text"
            name="short_order"
            onChange={handleShortOrder}
            onBlur={handleBlur}
            value={state.short_order}
          />
          <small>Quantity</small>
        </Col>
      </Row>
      <Row className="u-margin-bottom">
        <Col md="6" sm="12">
          <Label htmlFor="stop_loss">Stop Loss</Label>
          <InputGroup>
            <Input
              type="number"
              name="stop_loss"
              onChange={handleChange}
              onBlur={handleBlur}
              value={state.stop_loss}
            />
            <InputGroupAddon addonType="append">
              <InputGroupText>%</InputGroupText>
            </InputGroupAddon>
            <FormFeedback
              valid={parseFloat(state.short_order) > 0 ? false : true}
            >
              Stop loss required if short order enabled
            </FormFeedback>
          </InputGroup>
        </Col>
      </Row>
    </TabPane>
  );
}
