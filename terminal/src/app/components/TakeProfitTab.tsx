import { type FC } from "react"
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
import { TabsKeys } from "../pages/BotDetail"
import InputTooltip from "./InputTooltip"

const TakeProfit: FC = () => {
  const dispatch = useAppDispatch()
  const props = useAppSelector(selectBot)

  const {
    register,
    getValues,
    formState: { errors },
  } = useForm({
    mode: "onTouched",
    reValidateMode: "onBlur",
    defaultValues: {
      take_profit: props.take_profit,
      trailling: props.trailling,
      trailling_deviation: props.trailling_deviation,
      dynamic_trailling: props.dynamic_trailling,
    },
  })

  const handleBlur = (e: React.FocusEvent<HTMLInputElement>) => {
    const value = getValues(e.target.name as "take_profit" | "trailling_deviation")
    if (value)
    dispatch(setField({ name: e.target.name, value: value }))
  }

  return (
    <Tab.Pane eventKey={TabsKeys.TAKEPROFIT}>
      <Container>
        <Row className="my-3">
          <Col md="6" sm="12">
            <Form.Label htmlFor="take_profit">
              Take profit at <span className="u-required">*</span>
            </Form.Label>
            <InputGroup size="sm">
              <Form.Control
                type="number"
                name="take_profit"
                id="take_profit"
                onBlur={handleBlur}
                defaultValue={props.take_profit}
                {...register("take_profit", {
                  required: "Take profit is required",
                  min: {
                    value: 0,
                    message: "Minimum take profit is 1",
                  },
                  max: {
                    value: 100,
                    message: "Maximum take profit is 100",
                  },
                })}
              />
              <InputGroupText>%</InputGroupText>
            </InputGroup>
            {errors.take_profit && (
              <Form.Control.Feedback>
                {errors.take_profit.message}
              </Form.Control.Feedback>
            )}
          </Col>
          <Col md="3" sm="12">
            <Form.Group>
              <Form.Label htmlFor="trailling">Trailling</Form.Label>
              <br />
              <ButtonGroup>
                <ToggleButton
                  id="trailling"
                  className="position-relative"
                  checked={props.trailling}
                  value={1}
                  variant={props.trailling ? "primary" : "secondary"}
                  onClick={e => dispatch(setToggle({ name: "trailling", value: !props.trailling }))}
                >
                  {props.trailling ? "On" : "Off"}
                </ToggleButton>
              </ButtonGroup>
              <Form.Control.Feedback tooltip>{"Trailling won't trigger until trailling_stop_loss > base"}</Form.Control.Feedback>
            </Form.Group>
          </Col>
          <Col md="3" sm="12">
          <Form.Group>
              <Form.Label htmlFor="dynamic_trailling">Dynamic trailling</Form.Label>
              <br />
              <ButtonGroup>
                <ToggleButton
                  id="dynamic_trailling"
                  name="dynamic_trailling"
                  className="position-relative"
                  checked={props.dynamic_trailling}
                  value={1}
                  variant={props.dynamic_trailling ? "primary" : "secondary"}
                  onClick={e => dispatch(
                    setToggle({
                      name: "dynamic_trailling",
                      value: !props.dynamic_trailling,
                    }),
                  )}
                >
                  {props.dynamic_trailling ? "On" : "Off"}
                </ToggleButton>
              </ButtonGroup>
              <Form.Control.Feedback tooltip>{"Update the trailling_deviation according to volatility (SD)"}</Form.Control.Feedback>
            </Form.Group>
          </Col>
        </Row>
        <Row className="my-3">
          {props.trailling && (
            <Col md="6" sm="12">
              <Form.Label htmlFor="trailling_deviation">
                Trailling deviation
              </Form.Label>
              <InputGroup>
                <Form.Control
                  type="number"
                  name="trailling_deviation"
                  onBlur={handleBlur}
                  defaultValue={props.trailling_deviation}
                  {...register("trailling_deviation", {
                    required: "Trailling deviation in percentage is required",
                    min: {
                      value: 0,
                      message: "Minimum trailling deviation is 1",
                    },
                    max: {
                      value: 100,
                      message: "Maximum trailling deviation is 100",
                    },
                  })}
                />
                <InputGroupText>%</InputGroupText>
              </InputGroup>
            </Col>
          )}
        </Row>
      </Container>
    </Tab.Pane>
  )
}

export default TakeProfit
