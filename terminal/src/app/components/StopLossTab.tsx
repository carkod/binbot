import React, { type FC, useEffect } from "react";
import {
  ButtonGroup,
  Col,
  Container,
  Form,
  InputGroup,
  Row,
  Tab,
  ToggleButton,
} from "react-bootstrap";
import InputGroupText from "react-bootstrap/esm/InputGroupText";
import { useForm } from "react-hook-form";
import { selectBot, setField, setToggle } from "../../features/bots/botSlice";
import { useAppDispatch, useAppSelector } from "../hooks";
import { type AppDispatch } from "../store";
import { BotType, TabsKeys } from "../../utils/enums";
import {
  selectTestBot,
  setTestBotField,
  setTestBotToggle,
} from "../../features/bots/paperTradingSlice";

const StopLossTab: FC<{ botType?: BotType }> = ({ botType = "bots" }) => {
  const dispatch: AppDispatch = useAppDispatch();
  let { bot } = useAppSelector(selectBot);

  if (botType === BotType.PAPER_TRADING) {
    const testBot = useAppSelector(selectTestBot);
    bot = testBot.paperTrading;
  }

  const {
    watch,
    register,
    reset,
    formState: { errors },
  } = useForm({
    mode: "onTouched",
    reValidateMode: "onBlur",
    defaultValues: {
      stop_loss: bot.stop_loss,
      margin_short_reversal: bot.margin_short_reversal,
    },
  });

  useEffect(() => {
    const { unsubscribe } = watch((v, { name, type }) => {
      if (v && v?.[name]) {
        if (typeof v === "boolean") {
          if (botType === BotType.PAPER_TRADING) {
            dispatch(setTestBotToggle({ name, value: v[name] }));
          } else {
            dispatch(setToggle({ name, value: v[name] }));
          }
        } else {
          if (botType === BotType.PAPER_TRADING) {
            dispatch(
              setTestBotField({ name, value: v[name] as number | string }),
            );
          } else {
            dispatch(setField({ name, value: v[name] as number | string }));
          }
        }
      }
    });

    if (bot.id) {
      reset({
        stop_loss: bot.stop_loss,
        margin_short_reversal: bot.margin_short_reversal,
      });
    }

    return () => unsubscribe();
  }, [watch, dispatch, bot, reset]);

  const handleBlur = (e) => {
    if (e.target.value) {
      if (botType === BotType.PAPER_TRADING) {
        dispatch(
          setTestBotField({ name: e.target.name, value: watch(e.target.name) }),
        );
      } else {
        dispatch(
          setField({ name: e.target.name, value: watch(e.target.name) }),
        );
      }
    }
  };

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
                isInvalid={!!errors?.stop_loss}
                onBlur={(e) => handleBlur(e)}
                {...register("stop_loss", {
                  required: "Stop loss is required",
                  valueAsNumber: true,
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
                  variant={bot.margin_short_reversal ? "primary" : "secondary"}
                  value={1}
                  checked={bot.margin_short_reversal}
                  onClick={() => {
                    if (botType === BotType.PAPER_TRADING) {
                      dispatch(
                        setTestBotToggle({
                          name: "margin_short_reversal",
                          value: !bot.margin_short_reversal,
                        }),
                      );
                    } else {
                      dispatch(
                        setToggle({
                          name: "margin_short_reversal",
                          value: !bot.margin_short_reversal,
                        }),
                      );
                    }
                  }}
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
  );
};

export default StopLossTab;
