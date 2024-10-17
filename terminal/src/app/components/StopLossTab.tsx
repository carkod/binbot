import { type FC, useState } from "react"
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
import { useForm } from "react-hook-form"
import { selectBot, setField, setToggle } from "../../features/bots/botSlice"
import { useAppDispatch, useAppSelector } from "../hooks"
import { type AppDispatch } from "../store"
import { TabsKeys } from "../../utils/enums"

const StopLossTab: FC<{}> = () => {
  const dispatch: AppDispatch = useAppDispatch()
  const props = useAppSelector(selectBot)
  const [stopLossState, setStopLossState] = useState<number>(props.stop_loss)
  const [marginShortReversal, setMarginShortReversal] = useState<boolean>(props.margin_short_reversal)
  const {
    register,
    getValues,
    formState: { errors },
  } = useForm({
    defaultValues: {
      stop_loss: props.stop_loss,
      margin_short_reversal: props.margin_short_reversal,
    }
  })

  const handleBlur = (e: React.FocusEvent<HTMLInputElement>) => {
    const stopLossValue = getValues("stop_loss")
    if (stopLossValue) {
      dispatch(setField({ name: "stop_loss", value: stopLossValue }))
    }
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
                defaultValue={props.stop_loss}
                isInvalid={!!errors?.stop_loss}
                {...register("stop_loss", {
                  required: "Stop loss is required",
                  valueAsNumber: true,
                  min: 0,
                  max: 100,
                })}
              />
              <InputGroupText>%</InputGroupText>
              {errors.stop_loss && (
                <Form.Control.Feedback type="invalid">
                  {errors.stop_loss?.message}
                </Form.Control.Feedback>
              )}
            </InputGroup>
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
                  variant={props.margin_short_reversal ? "primary" : "secondary"}
                  value={1}
                  checked={props.margin_short_reversal}
                  onClick={() => {
                    dispatch(setToggle({ name: "margin_short_reversal", value: !props.margin_short_reversal }))
                  }}
                >
                  {props.margin_short_reversal ? "On" : "Off"}
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
