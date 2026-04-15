import React, { useEffect, type FC } from "react";
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
import { BotType, TabsKeys } from "../../utils/enums";
import {
  selectTestBot,
  setTestBotField,
  setTestBotToggle,
} from "../../features/bots/paperTradingSlice";

const TakeProfit: FC<{ botType?: BotType }> = ({ botType = BotType.BOTS }) => {
  const dispatch = useAppDispatch();
  let { bot } = useAppSelector(selectBot);

  if (botType === BotType.PAPER_TRADING) {
    const testBot = useAppSelector(selectTestBot);
    bot = testBot.paperTrading;
  }

  const {
    register,
    watch,
    reset,
    formState: { errors },
  } = useForm({
    mode: "onTouched",
    reValidateMode: "onBlur",
    defaultValues: {
      take_profit: bot.take_profit,
      trailing: bot.trailing,
      trailing_deviation: bot.trailing_deviation,
      trailing_profit: bot.trailing_profit,
      dynamic_trailing: bot.dynamic_trailing,
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
        take_profit: bot.take_profit,
        trailing: bot.trailing,
        trailing_deviation: bot.trailing_deviation,
        dynamic_trailing: bot.dynamic_trailing,
        trailing_profit: bot.trailing_profit,
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
    <Tab.Pane eventKey={TabsKeys.TAKEPROFIT}>
      <Container>
        <Row className="my-3">
          {bot.trailing ? (
            <Col md="6" sm="12">
              <Form.Label htmlFor="trailing_profit">
                Trail profit at <span className="u-required">*</span>
              </Form.Label>
              <InputGroup>
                <Form.Control
                  type="number"
                  name="trailing_profit"
                  onBlur={(e) => handleBlur(e)}
                  {...register("trailing_profit", {
                    required:
                      "Trailing profit in percentage is required when trailing is activated",
                    valueAsNumber: true,
                    min: {
                      value: 0,
                      message: "Minimum trailing profit is 1",
                    },
                    max: {
                      value: 100,
                      message: "Maximum trailing profit is 100",
                    },
                  })}
                />
                <InputGroupText>%</InputGroupText>
              </InputGroup>
            </Col>
          ) : (
            <Col md="6" sm="12">
              <Form.Label htmlFor="take_profit">
                Take profit at <span className="u-required">*</span>
              </Form.Label>
              <InputGroup size="sm">
                <Form.Control
                  type="number"
                  name="take_profit"
                  id="take_profit"
                  onBlur={(e) => handleBlur(e)}
                  {...register("take_profit", {
                    valueAsNumber: true,
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
                <Form.Control.Feedback type="invalid">
                  {errors.take_profit.message}
                </Form.Control.Feedback>
              )}
            </Col>
          )}
          <Col md="3" sm="12">
            <Form.Group>
              <Form.Label htmlFor="trailing">Trailing</Form.Label>
              <br />
              <ButtonGroup>
                <ToggleButton
                  id="trailing"
                  className="position-relative"
                  checked={bot.trailing}
                  value={1}
                  variant={bot.trailing ? "primary" : "secondary"}
                  onClick={(e) => {
                    if (botType === BotType.PAPER_TRADING) {
                      dispatch(
                        setTestBotToggle({
                          name: "trailing",
                          value: !bot.trailing,
                        }),
                      );
                    } else {
                      dispatch(
                        setToggle({ name: "trailing", value: !bot.trailing }),
                      );
                    }
                  }}
                >
                  {bot.trailing ? "On" : "Off"}
                </ToggleButton>
              </ButtonGroup>
              <Form.Control.Feedback tooltip>
                {"Trailing won't trigger until trailing_stop_loss > base"}
              </Form.Control.Feedback>
            </Form.Group>
          </Col>
          <Col md="3" sm="12">
            <Form.Group>
              <Form.Label htmlFor="dynamic_trailing">
                Dynamic trailing
              </Form.Label>
              <br />
              <ButtonGroup>
                <ToggleButton
                  id="dynamic_trailing"
                  name="dynamic_trailing"
                  className="position-relative"
                  checked={bot.dynamic_trailing}
                  value={1}
                  variant={bot.dynamic_trailing ? "primary" : "secondary"}
                  onClick={(e) => {
                    if (botType === BotType.PAPER_TRADING) {
                      dispatch(
                        setTestBotToggle({
                          name: "dynamic_trailing",
                          value: !bot.dynamic_trailing,
                        }),
                      );
                    } else {
                      dispatch(
                        setToggle({
                          name: "dynamic_trailing",
                          value: !bot.dynamic_trailing,
                        }),
                      );
                    }
                  }}
                >
                  {bot.dynamic_trailing ? "On" : "Off"}
                </ToggleButton>
              </ButtonGroup>
              <Form.Control.Feedback tooltip>
                {"Update the trailing_deviation according to volatility (SD)"}
              </Form.Control.Feedback>
            </Form.Group>
          </Col>
        </Row>
        <Row className="my-3">
          {bot.trailing && (
            <Col md="6" sm="12">
              <Form.Label htmlFor="trailing_deviation">
                Trailing deviation
              </Form.Label>
              <InputGroup>
                <Form.Control
                  type="number"
                  name="trailing_deviation"
                  onBlur={(e) => handleBlur(e)}
                  {...register("trailing_deviation", {
                    required:
                      "Trailing deviation in percentage is required when trailing is activated",
                    valueAsNumber: true,
                    min: {
                      value: 0,
                      message: "Minimum trailing deviation is 1",
                    },
                    max: {
                      value: 100,
                      message: "Maximum trailing deviation is 100",
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
  );
};

export default TakeProfit;
