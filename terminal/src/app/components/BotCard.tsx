import {
  Badge,
  Box,
  Button,
  Card,
  Grid,
  Group,
  Text,
  Title,
  VisuallyHidden,
} from "@mantine/core";
import { type FC } from "react";
import { useLocation, useNavigate } from "react-router";
import { type Bot } from "../../features/bots/botInitialState";
import { computeSingleBotProfit } from "../../features/bots/profits";
import { MarketType } from "../../utils/enums";
import { roundDecimals } from "../../utils/math";
import { formatTimestamp, renderDuration } from "../../utils/time";
type handleCallback = (id: string) => void;
interface BotCardProps {
  bot: Bot;
  botIndex?: number; // Selected bot index, this can be one of the selectedCards array
  selectedCards?: string[]; // Collection of selected cards
  handleSelection?: handleCallback;
  handleDelete?: handleCallback;
}
/**
 * Dump component that displays bots
 * in a card format
 * All logic should be handled in the parent component
 * @param BotCardProps
 * @returns React.Component
 */
const BotCard: FC<BotCardProps> = ({
  bot,
  botIndex,
  selectedCards,
  handleSelection,
  handleDelete,
}) => {
  const botProfit = computeSingleBotProfit(bot);
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const selectedIds = selectedCards ?? [];
  return (
    <Card
      tabIndex={botIndex}
      className={selectedIds.includes(bot.id) ? "selected-card" : ""}
      mb="md"
    >
      <Box
        mb="sm"
        c="white"
        py={16}
        bg="info.5"
        style={{
          border: 0,
        }}
      >
        <Box
          display="flex"
          style={{
            alignItems: "center",
            gap: 8,
          }}
          component="div"
        >
          <Text fw={600} component="span">
            <i className="fa-solid fa-chart-line fa-lg" />{" "}
            {bot.market_type || String(MarketType.SPOT).toUpperCase()}
          </Text>
        </Box>
      </Box>
      <br aria-hidden="true" />
      <Box>
        <Box w="100%">
          <Grid>
            <Grid.Col span={{ base: 12, md: 7 }}>
              <Title order={5}>{bot.pair}</Title>
              <Text c="dimmed" fw={300}>
                {bot.name}
              </Text>
            </Grid.Col>
            <Grid.Col span={{ base: 12, md: 5 }}>
              <Badge
                color={botProfit > 0 ? "success" : "danger"}
                variant="light"
              >
                {roundDecimals(botProfit)}%
              </Badge>
              <br />
              <Badge
                color={
                  bot.status === "active"
                    ? "success"
                    : bot.status === "pending"
                      ? "warning"
                      : bot.status === "error"
                        ? "danger"
                        : bot.status === "completed"
                          ? "info"
                          : "secondary"
                }
                variant="light"
              >
                <span>{bot.status && bot.status.toUpperCase()}</span>
              </Badge>
            </Grid.Col>
          </Grid>
          <hr />
          <Grid>
            <Grid.Col span={{ base: 7, md: 6 }}>
              <Text>Mode</Text>
            </Grid.Col>
            <Grid.Col span={{ base: 5, md: 6 }}>
              <Text tt="capitalize">{bot.mode ? bot.mode : "Unknown"}</Text>
            </Grid.Col>
          </Grid>
          <Grid>
            <Grid.Col span={{ base: 7, md: 6 }}>
              <Text>Position</Text>
            </Grid.Col>
            <Grid.Col span={{ base: 5, md: 6 }}>
              <Text tt="capitalize">{bot.position}</Text>
            </Grid.Col>
          </Grid>
          {bot.market_type === MarketType.FUTURES && (
            <Grid>
              <Grid.Col span={{ base: 7, md: 6 }}>
                <Text>Leverage</Text>
              </Grid.Col>
              <Grid.Col span={{ base: 5, md: 6 }}>
                <Text>
                  {bot.futures_leverage != null
                    ? `${bot.futures_leverage}x`
                    : "—"}
                </Text>
              </Grid.Col>
            </Grid>
          )}
          <Grid>
            <Grid.Col span={{ base: 7, md: 6 }}>
              <Text>Open @</Text>
            </Grid.Col>
            <Grid.Col span={{ base: 5, md: 6 }}>
              <Text>
                {(bot.deal?.opening_price &&
                  roundDecimals(bot.deal.opening_price, 6)) ||
                  bot.deal?.opening_qty}
              </Text>
            </Grid.Col>
          </Grid>
          {bot.deal?.opening_timestamp > 0 && (
            <Grid>
              <Grid.Col span={{ base: 7, md: 6 }}>
                <Text>Open time</Text>
              </Grid.Col>
              <Grid.Col span={{ base: 5, md: 6 }}>
                <Text>{formatTimestamp(bot.deal.opening_timestamp)}</Text>
              </Grid.Col>
            </Grid>
          )}
          {bot.trailing ? (
            <>
              <Grid>
                <Grid.Col span={{ base: 7, md: 6 }}>
                  <Text>Trailing profit</Text>
                </Grid.Col>
                <Grid.Col span={{ base: 5, md: 6 }}>
                  <Text>{roundDecimals(bot.trailing_profit) + "%"}</Text>
                </Grid.Col>
              </Grid>
              <Grid>
                <Grid.Col span={{ base: 7, md: 6 }}>
                  <Text>Trailing deviation</Text>
                </Grid.Col>
                <Grid.Col span={{ base: 5, md: 6 }}>
                  <Text>{roundDecimals(bot.trailing_deviation) + "%"}</Text>
                </Grid.Col>
              </Grid>
            </>
          ) : (
            <Grid>
              <Grid.Col span={{ base: 7, md: 6 }}>
                <Text>Take profit</Text>
              </Grid.Col>
              <Grid.Col span={{ base: 5, md: 6 }}>
                <Text>{roundDecimals(bot.take_profit) + "%"}</Text>
              </Grid.Col>
            </Grid>
          )}

          {bot.stop_loss > 0 && (
            <Grid>
              <Grid.Col span={{ base: 7, md: 6 }}>
                <Text>Stop loss</Text>
              </Grid.Col>
              <Grid.Col span={{ base: 5, md: 6 }}>
                <Text>{roundDecimals(bot.stop_loss) + "%"}</Text>
              </Grid.Col>
            </Grid>
          )}

          {bot.deal?.total_commissions > 0 && (
            <Grid>
              <Grid.Col span={{ base: 7, md: 6 }}>
                <Text>Commissions</Text>
              </Grid.Col>
              <Grid.Col span={{ base: 5, md: 6 }}>
                <Text>{`${bot.deal.total_commissions} ${bot.quote_asset}`}</Text>
              </Grid.Col>
            </Grid>
          )}
          {bot.deal?.total_interests > 0 && (
            <Grid>
              <Grid.Col span={{ base: 7, md: 6 }}>
                <Text>Interests</Text>
              </Grid.Col>
              <Grid.Col span={{ base: 5, md: 6 }}>
                <Text>{`${bot.deal.total_interests} ${bot.quote_asset}`}</Text>
              </Grid.Col>
            </Grid>
          )}

          {bot.deal?.closing_timestamp > 0 && (
            <Grid>
              <Grid.Col span={{ base: 7, md: 6 }}>
                <Text>Close time</Text>
              </Grid.Col>
              <Grid.Col span={{ base: 5, md: 6 }}>
                <Text>{formatTimestamp(bot.deal.closing_timestamp)}</Text>
              </Grid.Col>
            </Grid>
          )}
          {bot.deal?.closing_timestamp > 0 && (
            <Grid>
              <Grid.Col span={{ base: 7, md: 6 }}>
                <Text>Duration</Text>
              </Grid.Col>
              <Grid.Col span={{ base: 5, md: 6 }}>
                <Text>{renderDuration(bot)}</Text>
              </Grid.Col>
            </Grid>
          )}
        </Box>
      </Box>
      <hr />
      <Group
        mt="sm"
        display="flex"
        style={{
          flexDirection: "row",
          justifyContent: "space-between",
        }}
      >
        <Button
          title="Edit this bot"
          onClick={() => {
            if (bot.market_type === MarketType.FUTURES) {
              navigate(`/bots/futures/edit/${bot.id}`, {
                state: { bot: bot },
              });
            } else {
              navigate(`/bots/edit/${bot.id}`, {
                state: { bot: bot },
              });
            }
          }}
          color="info"
          type="button"
        >
          <i className="fa-solid fa-edit bot-edit-icon" />
        </Button>
        <Button
          onClick={() => handleSelection(bot.id)}
          color="success"
          type="button"
        >
          <i className="fa-solid fa-check" />
          <VisuallyHidden>
            {selectedIds.includes(bot.id) ? "Deselect" : "Select"}
          </VisuallyHidden>
        </Button>
        <Button
          onClick={() => handleDelete(bot.id)}
          color="danger"
          type="button"
        >
          <i className="fa-solid fa-trash" />
          <VisuallyHidden>Delete</VisuallyHidden>
        </Button>
      </Group>
    </Card>
  );
};
export default BotCard;
