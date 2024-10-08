import { type FC, useEffect } from "react"
import {
  ButtonGroup,
  Col,
  Container,
  Form,
  InputGroup,
  Row,
  Tab,
  ToggleButton
} from "react-bootstrap"
import InputGroupText from "react-bootstrap/esm/InputGroupText"
import { useForm } from "react-hook-form"
import { type Bot, singleBot } from "../../features/bots/botInitialState"
import { setField, setToggle } from "../../features/bots/botSlice"
import { useAppDispatch } from "../hooks"
import { TabsKeys } from "../pages/BotDetail"
import { type AppDispatch } from "../store"
import { InputTooltip } from "./InputTooltip"

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

  const {
    register,
    watch,
    formState: { errors },
  } = useForm<Bot>({
    mode: "onTouched",
    reValidateMode: "onSubmit",
    defaultValues: singleBot,
  })

  useEffect(() => {
    const subscription = watch((value, { name, type }) => {
      console.log(">>", value, name, type)
    })

    return () => subscription.unsubscribe()
  }, [watch])

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
              />
              <InputGroupText>%</InputGroupText>
            </InputGroup>
            <Form.Control.Feedback>Not a percentage</Form.Control.Feedback>
          </Col>
          <Col md="6" sm="12">
            <Form.Label htmlFor="name">Name</Form.Label>
            <Form.Control
              type="text"
              name="name"
              defaultValue={bot.name}
              {...register("name")}
            />
          </Col>
        </Row>
        <Row className="my-3">
          <Col md="6" sm="12">
            <InputTooltip
              name="margin_short_reversal"
              tooltip={"Autoswitch (reversal)"}
              label="Margin short reversal"
              errors={errors}
              required
            >
              <Form.Control
                type="number"
                name="stop_loss"
                onBlur={handleBlur}
                defaultValue={bot.stop_loss}
              />
            </InputTooltip>
          </Col>

          <Col>
            <ButtonGroup>
              <ToggleButton
                id="margin-short-reversal"
                checked={bot.margin_short_reversal}
                value={1}
                onChange={e => toggleAutoswitch(e.currentTarget.checked)}
              >
                Toggle Margin short reversal
              </ToggleButton>
            </ButtonGroup>
          </Col>
        </Row>
      </Container>
    </Tab.Pane>
  )
}

export default StopLossTab
