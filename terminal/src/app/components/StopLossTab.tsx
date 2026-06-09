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
import {
  selectBot,
  setField,
  setRecoveryParams,
  setToggle,
} from "../../features/bots/botSlice";
import { useAppDispatch, useAppSelector } from "../hooks";
import { type AppDispatch } from "../store";
import { BotType, TabsKeys } from "../../utils/enums";
import {
  selectTestBot,
  setTestBotField,
  setTestBotToggle,
} from "../../features/bots/paperTradingSlice";
import type { RecoveryParams } from "../../features/bots/botInitialState";
import { defaultRecoveryParams } from "../../features/bots/botInitialState";

const StopLossTab: FC<{ botType?: BotType }> = ({ botType = "bots" }) => {
  const dispatch: AppDispatch = useAppDispatch();
  const { bot: liveBot } = useAppSelector(selectBot);
  const { paperTrading } = useAppSelector(selectTestBot);
  const bot = botType === BotType.PAPER_TRADING ? paperTrading : liveBot;
  const recoveryEnabled =
    botType !== BotType.PAPER_TRADING && bot.recovery_params != null;

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
    const { unsubscribe } = watch((values, { name }) => {
      const value = name ? values[name] : undefined;
      if (name && value !== undefined) {
        if (typeof value === "boolean") {
          if (botType === BotType.PAPER_TRADING) {
            dispatch(setTestBotToggle({ name, value }));
          } else {
            dispatch(setToggle({ name, value }));
          }
        } else {
          if (botType === BotType.PAPER_TRADING) {
            dispatch(
              setTestBotField({ name, value: value as number | string }),
            );
          } else {
            dispatch(setField({ name, value: value as number | string }));
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
  }, [watch, dispatch, bot, reset, botType]);

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

  const handleRecoveryToggle = () => {
    dispatch(
      setRecoveryParams(recoveryEnabled ? null : { ...defaultRecoveryParams }),
    );
  };

  const handleRecoveryChange = (
    name: keyof RecoveryParams,
    value: RecoveryParams[keyof RecoveryParams],
  ) => {
    dispatch(
      setRecoveryParams({
        ...defaultRecoveryParams,
        ...bot.recovery_params,
        [name]: value,
      }),
    );
  };

  return (
    <Tab.Pane
      id={TabsKeys.STOPLOSS}
      eventKey={TabsKeys.STOPLOSS}
      className="mb-3"
    >
      <Container>
        <Row className="my-3">
          <Col md={botType === BotType.PAPER_TRADING ? 6 : 4} sm="12">
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
                    message: "Minimum trailing deviation is 1",
                  },
                  max: {
                    value: 100,
                    message: "Maximum trailing deviation is 100",
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
          <Col md={botType === BotType.PAPER_TRADING ? 6 : 4} sm="12">
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
                Autoswitch position to short or long
              </Form.Control.Feedback>
            </Form.Group>
          </Col>
          {botType !== BotType.PAPER_TRADING && (
            <Col md="4" sm="12">
              <Form.Group className="position-relative">
                <Form.Label htmlFor="recovery_mode">Recovery mode</Form.Label>
                <br />
                <ButtonGroup className="mb-2">
                  <ToggleButton
                    id="recovery_mode"
                    type="checkbox"
                    name="recovery_mode"
                    variant={recoveryEnabled ? "primary" : "secondary"}
                    value={1}
                    checked={recoveryEnabled}
                    onChange={handleRecoveryToggle}
                  >
                    {recoveryEnabled ? "On" : "Off"}
                  </ToggleButton>
                </ButtonGroup>
              </Form.Group>
            </Col>
          )}
        </Row>
        {recoveryEnabled && (
          <Row className="my-3">
            <Col md="3" sm="12">
              <Form.Label htmlFor="reversal_path">Reversal path</Form.Label>
              <Form.Select
                id="reversal_path"
                value={bot.recovery_params?.reversal_path ?? "source"}
                onChange={(event) =>
                  handleRecoveryChange(
                    "reversal_path",
                    event.target.value as RecoveryParams["reversal_path"],
                  )
                }
              >
                <option value="source">Source</option>
                <option value="recovery">Recovery</option>
              </Form.Select>
            </Col>
            <Col md="3" sm="12">
              <Form.Label htmlFor="source_contracts">
                Source contracts
              </Form.Label>
              <Form.Control
                id="source_contracts"
                type="number"
                min={0}
                step="any"
                value={bot.recovery_params?.source_contracts ?? 0}
                onChange={(event) =>
                  handleRecoveryChange(
                    "source_contracts",
                    Number(event.target.value) || 0,
                  )
                }
              />
            </Col>
            <Col md="3" sm="12">
              <Form.Label htmlFor="source_loss_fiat">
                Source loss ({bot.fiat ?? "fiat"})
              </Form.Label>
              <Form.Control
                id="source_loss_fiat"
                type="number"
                min={0}
                step="any"
                value={bot.recovery_params?.source_loss_fiat ?? 0}
                onChange={(event) =>
                  handleRecoveryChange(
                    "source_loss_fiat",
                    Number(event.target.value) || 0,
                  )
                }
              />
            </Col>
            <Col md="3" sm="12">
              <Form.Label htmlFor="recovery_stop_loss_pct">
                Recovery stop loss
              </Form.Label>
              <InputGroup size="sm">
                <Form.Control
                  id="recovery_stop_loss_pct"
                  type="number"
                  min={0}
                  max={100}
                  step="any"
                  value={bot.recovery_params?.stop_loss_pct ?? 0}
                  onChange={(event) =>
                    handleRecoveryChange(
                      "stop_loss_pct",
                      Number(event.target.value) || 0,
                    )
                  }
                />
                <InputGroupText>%</InputGroupText>
              </InputGroup>
            </Col>
          </Row>
        )}
      </Container>
    </Tab.Pane>
  );
};

export default StopLossTab;
