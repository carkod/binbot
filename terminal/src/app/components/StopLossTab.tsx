import { formGridBreakpoints } from "../../theme";
import { Box, Grid, Group, Input, Tabs, Text, TextInput } from "@mantine/core";
import { type FC, useEffect } from "react";
import { useForm } from "react-hook-form";
import type { RecoveryParams } from "../../features/bots/botInitialState";
import { defaultRecoveryParams } from "../../features/bots/botInitialState";
import {
  focusOrderLine,
  selectBot,
  setField,
  setRecoveryParams,
  setToggle,
} from "../../features/bots/botSlice";
import { TabsKeys } from "../../utils/enums";
import { useAppDispatch, useAppSelector } from "../hooks";
import { type AppDispatch } from "../store";
const StopLossTab: FC = () => {
  const dispatch: AppDispatch = useAppDispatch();
  const { bot: liveBot } = useAppSelector(selectBot);
  const bot = liveBot;
  const recoveryEnabled = bot.recovery_params != null;
  const {
    watch,
    register,
    setValue,
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
      if (
        name &&
        value !== undefined &&
        (typeof value !== "number" || Number.isFinite(value))
      ) {
        if (typeof value === "boolean") {
          dispatch(setToggle({ name, value }));
        } else {
          dispatch(setField({ name, value: value as number | string }));
        }
      }
    });
    return () => unsubscribe();
  }, [watch, dispatch]);
  useEffect(() => {
    setValue("stop_loss", bot.stop_loss);
  }, [bot.stop_loss, setValue]);
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
    <Tabs.Panel
      id={TabsKeys.STOPLOSS}
      value={TabsKeys.STOPLOSS}
      pt="md"
      mb={16}
    >
      <Box w="100%">
        <Grid type="container" breakpoints={formGridBreakpoints} my={16}>
          <Grid.Col
            span={{
              base: 12,
              sm: 12,
              md: 4,
            }}
          >
            <Input.Label htmlFor="stop_loss">
              Stop loss{" "}
              <Text c="danger.8" component="span">
                *
              </Text>
            </Input.Label>
            <Group gap="xs" wrap="nowrap" className="field-row">
              <TextInput
                type="number"
                step="any"
                name="stop_loss"
                id="stop_loss"
                onFocus={() => dispatch(focusOrderLine("stop_loss"))}
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
                error={!!errors?.stop_loss}
              />
              <Text component="span" c="dimmed">
                %
              </Text>
              {errors.stop_loss && (
                <Input.Error>{errors.stop_loss?.message}</Input.Error>
              )}
            </Group>
          </Grid.Col>
        </Grid>
        {recoveryEnabled && (
          <Grid type="container" breakpoints={formGridBreakpoints} my={16}>
            <Grid.Col
              span={{
                base: 12,
                sm: 12,
                md: 3,
              }}
            >
              <Input.Label htmlFor="recovery_stop_loss_pct">
                Recovery stop loss
              </Input.Label>
              <Group gap="xs" wrap="nowrap" className="field-row">
                <TextInput
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
                <Text component="span" c="dimmed">
                  %
                </Text>
              </Group>
            </Grid.Col>
          </Grid>
        )}
      </Box>
    </Tabs.Panel>
  );
};
export default StopLossTab;
