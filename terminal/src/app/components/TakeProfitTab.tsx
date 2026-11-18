import { formGridBreakpoints } from "../../theme";
import {
  Box,
  Grid,
  Group,
  Input,
  SimpleGrid,
  Switch,
  Tabs,
  Text,
  TextInput,
} from "@mantine/core";
import { useEffect, type FC } from "react";
import { useForm } from "react-hook-form";
import {
  focusOrderLine,
  selectBot,
  setField,
  setToggle,
} from "../../features/bots/botSlice";
import { TabsKeys } from "../../utils/enums";
import { useAppDispatch, useAppSelector } from "../hooks";

const TakeProfit: FC = () => {
  const dispatch = useAppDispatch();

  const { bot } = useAppSelector(selectBot);

  const {
    register,
    reset,
    setValue,
    formState: { errors },
  } = useForm({
    mode: "onTouched",
    reValidateMode: "onBlur",
    defaultValues: {
      take_profit: bot.take_profit,
      trailing_deviation: bot.trailing_deviation,
      trailing_profit: bot.trailing_profit,
    },
  });

  useEffect(() => {
    reset({
      take_profit: bot.take_profit,
      trailing_deviation: bot.trailing_deviation,
      trailing_profit: bot.trailing_profit,
    });
    // A new bot needs new defaults; local field edits must not reset the form.
  }, [bot.id, reset]);
  useEffect(() => {
    setValue("take_profit", bot.take_profit);
  }, [bot.take_profit, setValue]);
  useEffect(() => {
    setValue("trailing_profit", bot.trailing_profit);
  }, [bot.trailing_profit, setValue]);
  useEffect(() => {
    setValue("trailing_deviation", bot.trailing_deviation);
  }, [bot.trailing_deviation, setValue]);

  const commitPercentage = (
    name: "take_profit" | "trailing_profit" | "trailing_deviation",
    value: string,
  ) => {
    if (value === "") return;

    const percentage = Number(value);

    if (Number.isFinite(percentage)) {
      dispatch(setField({ name, value: percentage }));
    }
  };

  return (
    <Tabs.Panel value={TabsKeys.TAKEPROFIT} pt="md">
      <Box w="100%">
        <Grid type="container" breakpoints={formGridBreakpoints} my={16}>
          {bot.trailing ? (
            <Grid.Col span={{ base: 12, md: 6 }}>
              <Input.Label htmlFor="trailing_profit">
                Trail profit at{" "}
                <Text c="danger.8" component="span">
                  *
                </Text>
              </Input.Label>
              <Group gap="xs" wrap="nowrap" className="field-row">
                <TextInput
                  type="number"
                  name="trailing_profit"
                  id="trailing_profit"
                  step="any"
                  onFocus={() => dispatch(focusOrderLine("trailing_profit"))}
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
                    onBlur: (event) =>
                      commitPercentage("trailing_profit", event.target.value),
                  })}
                />
                <Text component="span" c="dimmed">
                  %
                </Text>
              </Group>
            </Grid.Col>
          ) : (
            <Grid.Col span={{ base: 12, md: 6 }}>
              <Input.Label htmlFor="take_profit">
                Take profit at{" "}
                <Text c="danger.8" component="span">
                  *
                </Text>
              </Input.Label>
              <Group gap="xs" wrap="nowrap" className="field-row">
                <TextInput
                  type="number"
                  name="take_profit"
                  id="take_profit"
                  onFocus={() => dispatch(focusOrderLine("take_profit"))}
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
                    onBlur: (event) =>
                      commitPercentage("take_profit", event.target.value),
                  })}
                />
                <Text component="span" c="dimmed">
                  %
                </Text>
              </Group>
              {errors.take_profit && (
                <Input.Error>{errors.take_profit.message}</Input.Error>
              )}
            </Grid.Col>
          )}
          <Grid.Col span={{ base: 12, md: 3 }}>
            <Box>
              <Input.Label htmlFor="trailing">Trailing</Input.Label>
              <Group gap="xs" mih={36}>
                <Switch
                  id="trailing"
                  name="trailing"
                  checked={bot.trailing}
                  onChange={() => {
                    dispatch(
                      setToggle({ name: "trailing", value: !bot.trailing }),
                    );
                  }}
                  label={bot.trailing ? "On" : "Off"}
                />
              </Group>
            </Box>
          </Grid.Col>
          <Grid.Col span={{ base: 12, md: 3 }}>
            <Box>
              <Input.Label htmlFor="dynamic_trailing">
                Dynamic trailing
              </Input.Label>
              <Group gap="xs" mih={36}>
                <Switch
                  id="dynamic_trailing"
                  name="dynamic_trailing"
                  checked={bot.dynamic_trailing}
                  onChange={() => {
                    dispatch(
                      setToggle({
                        name: "dynamic_trailing",
                        value: !bot.dynamic_trailing,
                      }),
                    );
                  }}
                  label={bot.dynamic_trailing ? "On" : "Off"}
                />
              </Group>
            </Box>
          </Grid.Col>
        </Grid>
        <SimpleGrid
          cols={{ base: 1, [formGridBreakpoints.md]: 2 }}
          type="container"
          my={16}
        >
          {bot.trailing && (
            <Box>
              <Input.Label htmlFor="trailing_deviation">
                Trailing deviation
              </Input.Label>
              <Group gap="xs" wrap="nowrap" className="field-row">
                <TextInput
                  type="number"
                  name="trailing_deviation"
                  id="trailing_deviation"
                  step="any"
                  onFocus={() => dispatch(focusOrderLine("trailing_deviation"))}
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
                    onBlur: (event) =>
                      commitPercentage(
                        "trailing_deviation",
                        event.target.value,
                      ),
                  })}
                />
                <Text component="span" c="dimmed">
                  %
                </Text>
              </Group>
            </Box>
          )}
        </SimpleGrid>
      </Box>
    </Tabs.Panel>
  );
};

export default TakeProfit;
