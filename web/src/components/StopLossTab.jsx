import {
  Col,
  FormFeedback,
  Input,
  InputGroup,
  InputGroupText,
  Label,
  Row,
  TabPane,
  Button
} from "reactstrap";
import BotFormTooltip from "./BotFormTooltip";

export default function StopLossTab({
  stopLossError,
  handleChange,
  handleBlur,
  stop_loss,
  margin_short_reversal,
  toggleAutoswitch,
  strategy="long"
}) {
  return (
    <TabPane tabId="stop-loss">
      <Row className="u-margin-bottom">
        <Col md="6" sm="12">
          <Label htmlFor="stop_loss">
            Stop loss <span className="u-required">*</span>
          </Label>
          <InputGroup size="sm">
            <Input
              type="number"
              name="stop_loss"
              onChange={handleChange}
              onBlur={handleBlur}
              value={stop_loss}
            />
            <InputGroupText>%</InputGroupText>
          </InputGroup>
          <FormFeedback valid={!stopLossError}>Not a percentage</FormFeedback>
        </Col>
        {strategy === "margin_short" && (
          <Col md="6" sm="12">
            <BotFormTooltip
              name="margin_short_reversal"
              text={"Autoswitches to long bot"}
            >
              Autoswitch (reversal)
            </BotFormTooltip>
            <br />
            <Button
              color={margin_short_reversal ? "success" : "secondary"}
              onClick={() => toggleAutoswitch(!margin_short_reversal)}
            >
              {margin_short_reversal ? "On" : "Off"}
            </Button>
          
          </Col>
        )}
      </Row>
    </TabPane>
  );
}
