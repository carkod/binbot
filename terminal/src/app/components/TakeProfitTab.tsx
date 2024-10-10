import {
  Col,
  Container,
  Row,
  Tab,
  Form,
  ButtonGroup,
  ToggleButton,
  InputGroup,
} from "react-bootstrap"
import { TabsKeys } from "../pages/BotDetail"
import { useForm } from "react-hook-form"
import { type Bot, singleBot } from "../../features/bots/botInitialState"
import { type FC, useEffect, useState } from "react"
import InputTooltip from "./InputTooltip"
import { useAppDispatch } from "../hooks"
import { setField } from "../../features/bots/botSlice"
import InputGroupText from "react-bootstrap/esm/InputGroupText"
import { Input } from "react-bootstrap-typeahead"

const TakeProfit: FC<{
  bot: Bot
}> = ({ bot }) => {
  const [showTrailling, toggleTrailling] = useState<boolean>(bot.trailling)
  const dispatch = useAppDispatch()

  const {
    register,
    watch,
    formState: { errors },
  } = useForm<Bot>({
    mode: "onTouched",
    reValidateMode: "onSubmit",
    defaultValues: singleBot,
  })

  const handleBlur = (e: React.FocusEvent<HTMLInputElement>) => {
    const { name, value } = e.target
    dispatch(setField({ name, value }))
  }

  useEffect(() => {
    const subscription = watch((value, { name, type }) => {
      console.log(">>", value, name, type)
    })

    return () => subscription.unsubscribe()
  }, [watch])

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
                type="text"
                name="take_profit"
                id="take_profit"
                onBlur={handleBlur}
                defaultValue={bot.take_profit}
                {...register("take_profit", {
                  required: "Take profit is required",
                  min: {
                    value: 0.1,
                    message: "Minimum take profit is 1",
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
              <InputTooltip
                name="trailling"
                tooltip={
                  "Trailling won't trigger until trailling_stop_loss > base"
                }
                label="Trailling"
                errors={errors}
                required={true}
              >
                <Form.Control
                  type="text"
                  name="trailling"
                  onBlur={handleBlur}
                  defaultValue={bot.base_order_size}
                  autoComplete="off"
                  required
                  {...register("trailling", {
                    required: "Base order size is required",
                    min: {
                      value: 15,
                      message: "Minimum base order size is 15",
                    },
                  })}
                />
              </InputTooltip>
              <ButtonGroup>
                <ToggleButton
                  id="trailling"
                  checked={bot.trailling}
                  value={1}
                  onChange={e => toggleTrailling(e.currentTarget.checked)}
                >
                  Toggle Margin short reversal
                </ToggleButton>
              </ButtonGroup>
            </Form.Group>
          </Col>
          <Col md="3" sm="12">
            <Form.Group>
              <InputTooltip
                name="dynamic_trailling"
                tooltip={
                  "Update the trailling_deviation according to volatility (SD)"
                }
                label="Dynamic trailling"
                errors={errors}
                required={true}
              >
                Dynamic trailling
              </InputTooltip>
              <ButtonGroup>
                <ToggleButton
                  id="dynamic_trailling"
                  checked={bot.dynamic_trailling}
                  value={1}
                  // onChange={e => toggleAutoswitch(e.currentTarget.checked)}
                >
                  Toggle Dynamic trailling
                </ToggleButton>
              </ButtonGroup>
            </Form.Group>
          </Col>
        </Row>
        <Row className="my-3">
          {bot.trailling && (
            <Col md="6" sm="12">
              <Form.Label htmlFor="trailling_deviation">
                Trailling deviation
              </Form.Label>
              <InputGroup>
                <Form.Control
                  type="text"
                  name="trailling_deviation"
                  onBlur={handleBlur}
                  defaultValue={bot.trailling_deviation}
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
