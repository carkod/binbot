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

export default function StopLoss({
  stopLossError,
  handleChange,
  handleBlur,
  stop_loss,
}) {
  return (
    <TabPane tabId="stop-loss">
      <Row className="u-margin-bottom">
        <Col md="6" sm="12">
          <Label htmlFor="stop_loss">
            Stop loss <span className="u-required">*</span>
          </Label>
          <InputGroup>
            <Input
              type="text"
              name="stop_loss"
              onChange={handleChange}
              onBlur={handleBlur}
              value={stop_loss}
            />
            <InputGroupAddon addonType="append">
              <InputGroupText>%</InputGroupText>
            </InputGroupAddon>
          </InputGroup>
          <FormFeedback valid={!stopLossError}>Not a percentage</FormFeedback>
        </Col>
      </Row>
    </TabPane>
  );
}
