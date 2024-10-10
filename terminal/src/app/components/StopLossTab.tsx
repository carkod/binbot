import { type FC, useEffect } from "react"
import {
  ButtonGroup,
  Col,
  Container,
  Form,
  InputGroup,
  Row,
  Tab,
  ToggleButton,
} from "react-bootstrap"
import InputGroupText from "react-bootstrap/esm/InputGroupText"
import { useForm, useFormContext } from "react-hook-form"
import { type Bot, singleBot } from "../../features/bots/botInitialState"
import { setField, setToggle } from "../../features/bots/botSlice"
import { useAppDispatch } from "../hooks"
import { TabsKeys } from "../pages/BotDetail"
import { type AppDispatch } from "../store"

const StopLossTab: FC<{
  bot: Bot
}> = ({ bot }) => {
  const dispatch: AppDispatch = useAppDispatch()

  const handleBlur = (e: React.FocusEvent<HTMLInputElement>) => {
    const { name, value } = e.target
    dispatch(setField({ name, value }))
  }

  const toggleAutoswitch = (value: boolean) => {
    dispatch(setToggle({ name: "margin_short_reversal", value: value }))
  }


  return (
    <Tab.Pane
      id={TabsKeys.STOPLOSS}
      eventKey={TabsKeys.STOPLOSS}
      className="mb-3"
    >
      <Container>
        <Row className="my-3">
          <Col md="6" sm="12">
            <Form.Label htmlFor="stop_loss">
              Stop loss <span className="u-required">*</span>
            </Form.Label>
            <InputGroup size="sm">
              <Form.Control
                type="number"
                name="stop_loss"
                onBlur={handleBlur}
                defaultValue={bot.stop_loss}
                // {...register("stop_loss", {
                //   required: "Stop loss is required",
                // })}
              />
              <InputGroupText>%</InputGroupText>
            </InputGroup>
            <Form.Control.Feedback>Not a percentage</Form.Control.Feedback>
          </Col>
          <Col md="6" sm="12">
            <Form.Group className="position-relative">
              <Form.Label htmlFor="margin_short_reversal">
                Autoswitch (reversal)
              </Form.Label>
              <br />
              <ButtonGroup className="mb-2">
                <ToggleButton
                  id="margin_short_reversal"
                  type="radio"
                  name="margin_short_reversal"
                  variant={bot.margin_short_reversal ? "primary" : "secondary"}
                  value={1}
                  checked={bot.margin_short_reversal}
                  // {...register("margin_short_reversal")}
                >
                  {bot.margin_short_reversal ? "On" : "Off"}
                </ToggleButton>
              </ButtonGroup>
              <Form.Control.Feedback tooltip>
                Autoswitch strategy to margin short or long
              </Form.Control.Feedback>
            </Form.Group>
          </Col>
        </Row>
      </Container>
    </Tab.Pane>
  )
}

export default StopLossTab
