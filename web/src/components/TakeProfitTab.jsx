import {
  Button,
  Col,
  FormFeedback,
  FormGroup,
  Input,
  Label,
  Row,
  TabPane,
} from "reactstrap";
import BotFormTooltip from "./BotFormTooltip";

export default function TakeProfit({
  takeProfitError,
  take_profit,
  trailling,
  trailling_deviation,
  dynamic_trailling,
  handleChange,
  handleBlur,
  toggleTrailling,
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
        <Col md="3" sm="12">
          <FormGroup>
            <BotFormTooltip
              name="trailling"
              text={"Trailling won't trigger until trailling_stop_loss > base"}
            >
              Trailling
            </BotFormTooltip>
            <br />
            <Button
              name="trailling"
              color={trailling === "true" || trailling ? "success" : "secondary"}
              onClick={(e) => toggleTrailling(e.target.name)}
            >
              {trailling === "true" || trailling ? "On" : "Off"}
            </Button>
          </FormGroup>
        </Col>
        <Col md="3" sm="12">
          <FormGroup>
            <BotFormTooltip
              name="dynamic_trailling"
              text={"Update the trailling_deviation according to volatility (SD)"}
            >
              Dynamic trailling
            </BotFormTooltip>
            <br />
            <Button
              name="dynamic_trailling"
              color={dynamic_trailling ? "success" : "secondary"}
              onClick={(e) => toggleTrailling(e.target.name)}
            >
              {dynamic_trailling ? "On" : "Off"}
            </Button>
          </FormGroup>
        </Col>
      </Row>
      <Row className="u-margin-bottom">
        {(trailling || trailling === "true") && (
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
