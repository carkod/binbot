import { type FC, useEffect } from "react";
import { Col, Container, Form, InputGroup, Row, Tab } from "react-bootstrap";
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
import { TabsKeys } from "../../utils/enums";
import type { RecoveryParams } from "../../features/bots/botInitialState";
import { defaultRecoveryParams } from "../../features/bots/botInitialState";

const StopLossTab: FC = () => {
  const dispatch: AppDispatch = useAppDispatch();
  const { bot: liveBot } = useAppSelector(selectBot);
  const bot = liveBot;
  const recoveryEnabled = bot.recovery_params != null;

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
    },
  });

  useEffect(() => {
    const { unsubscribe } = watch((values, { name }) => {
      const value = name ? values[name] : undefined;
      if (name && value !== undefined) {
        if (typeof value === "boolean") {
          dispatch(setToggle({ name, value }));
        } else {
          dispatch(setField({ name, value: value as number | string }));
        }
      }
    });

    if (bot.id) {
      reset({
        stop_loss: bot.stop_loss,
      });
    }

    return () => unsubscribe();
  }, [watch, dispatch, bot, reset]);

  const handleBlur = (e) => {
    if (e.target.value) {
      dispatch(setField({ name: e.target.name, value: watch(e.target.name) }));
    }
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
          <Col md={4} sm="12">
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
        </Row>
        {recoveryEnabled && (
          <Row className="my-3">
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
