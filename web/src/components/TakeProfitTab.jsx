
import {
  Button,
  Col,
  FormFeedback,
  Input,
  Label,
  Row,
  TabPane,
} from "reactstrap";

export default function TakeProfit ({
  takeProfitError,
  take_profit,
  trailling,
  trailling_deviation,
  handleChange,
  handleBlur,
  toggleTrailling
}) {

  return (
    <TabPane tabId="take-profit">
      <Row className="u-margin-bottom">
        <Col md="6" sm="12">
          <Label for="take_profit">
            Take profit at (%): <span className="u-required">*</span>
          </Label>
          <Input
            invalid={takeProfitError}
            type="text"
            name="take_profit"
            id="take_profit"
            onChange={handleChange}
            onBlur={handleBlur}
            value={take_profit}
          />
          <FormFeedback>
            <strong>Take profit</strong> is required.
          </FormFeedback>
        </Col>
        <Col md="6" sm="12">
          <label>Trailling</label>
          <br />
          <Button
            color={trailling === "true" ? "success" : "secondary"}
            onClick={toggleTrailling}
          >
            {trailling === "true" ? "On" : "Off"}
          </Button>
        </Col>
      </Row>
      <Row className="u-margin-bottom">
        
        {trailling === "true" && (
          <Col md="6" sm="12">
            <Label htmlFor="trailling_deviation">Trailling deviation (%)</Label>
            <Input
              type="text"
              name="trailling_deviation"
              onChange={handleChange}
              onBlur={handleBlur}
              value={trailling_deviation}
            />
          </Col>
        )}
      </Row>
    </TabPane>
    );
  }
