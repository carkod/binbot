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
      trailling: bot.trailling,
      trailling_deviation: bot.trailling_deviation,
      trailling_profit: bot.trailling_profit,
      dynamic_trailling: bot.dynamic_trailling,
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
        trailling: bot.trailling,
        trailling_deviation: bot.trailling_deviation,
        dynamic_trailling: bot.dynamic_trailling,
        trailling_profit: bot.trailling_profit,
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
          {bot.trailling ? (
            <Col md="6" sm="12">
              <Form.Label htmlFor="trailling_profit">
                Trail profit at <span className="u-required">*</span>
              </Form.Label>
              <InputGroup>
                <Form.Control
                  type="number"
                  name="trailling_profit"
                  onBlur={(e) => handleBlur(e)}
                  {...register("trailling_profit", {
                    required:
                      "Trailling profit in percentage is required when trailling is activated",
                    valueAsNumber: true,
                    min: {
                      value: 0,
                      message: "Minimum trailling profit is 1",
                    },
                    max: {
                      value: 100,
                      message: "Maximum trailling profit is 100",
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
              <Form.Label htmlFor="trailling">Trailling</Form.Label>
              <br />
              <ButtonGroup>
                <ToggleButton
                  id="trailling"
                  className="position-relative"
                  checked={bot.trailling}
                  value={1}
                  variant={bot.trailling ? "primary" : "secondary"}
                  onClick={(e) => {
                    if (botType === BotType.PAPER_TRADING) {
                      dispatch(
                        setTestBotToggle({
                          name: "trailling",
                          value: !bot.trailling,
                        }),
                      );
                    } else {
                      dispatch(
                        setToggle({ name: "trailling", value: !bot.trailling }),
                      );
                    }
                  }}
                >
                  {bot.trailling ? "On" : "Off"}
                </ToggleButton>
              </ButtonGroup>
              <Form.Control.Feedback tooltip>
                {"Trailling won't trigger until trailling_stop_loss > base"}
              </Form.Control.Feedback>
            </Form.Group>
          </Col>
          <Col md="3" sm="12">
            <Form.Group>
              <Form.Label htmlFor="dynamic_trailling">
                Dynamic trailling
              </Form.Label>
              <br />
              <ButtonGroup>
                <ToggleButton
                  id="dynamic_trailling"
                  name="dynamic_trailling"
                  className="position-relative"
                  checked={bot.dynamic_trailling}
                  value={1}
                  variant={bot.dynamic_trailling ? "primary" : "secondary"}
                  onClick={(e) => {
                    if (botType === BotType.PAPER_TRADING) {
                      dispatch(
                        setTestBotToggle({
                          name: "dynamic_trailling",
                          value: !bot.dynamic_trailling,
                        }),
                      );
                    } else {
                      dispatch(
                        setToggle({
                          name: "dynamic_trailling",
                          value: !bot.dynamic_trailling,
                        }),
                      );
                    }
                  }}
                >
                  {bot.dynamic_trailling ? "On" : "Off"}
                </ToggleButton>
              </ButtonGroup>
              <Form.Control.Feedback tooltip>
                {"Update the trailling_deviation according to volatility (SD)"}
              </Form.Control.Feedback>
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
                  type="number"
                  name="trailling_deviation"
                  onBlur={(e) => handleBlur(e)}
                  {...register("trailling_deviation", {
                    required:
                      "Trailling deviation in percentage is required when trailling is activated",
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
              </InputGroup>
            </Col>
          )}
        </Row>
      </Container>
    </Tab.Pane>
  );
};

export default TakeProfit;
