import { Badge, Box, Button, Card, Grid, Group } from "@mantine/core";
import type { FC } from "react";
import { useNavigate } from "react-router";
import {
  calculateCloseAdjustmentPnl,
  calculateFilledLevelCount,
  calculateGridPnl,
  calculateGridUtilization,
  calculateLevelPnlSum,
  calculateOpenOrderCount,
  GridLadderStatus,
  isActiveGridLadder,
  type GridLadder,
} from "../../features/gridLadders/gridLadders";
import { returnBadgeBg } from "../../utils/grid-ladder";
import { roundDecimals } from "../../utils/math";
import { formatTimestamp } from "../../utils/time";
interface GridLadderCardProps {
  ladder: GridLadder;
  gridReturnPct: number;
  selected: boolean;
  onSelect: (id: string) => void;
  onClose: (id: string) => void;
  onDelete: (id: string) => void;
}
const statusColorMap: Record<GridLadderStatus, string> = {
  pending: "secondary",
  active: "success",
  closing: "warning",
  closed: "dark",
  range_broken: "danger",
  error: "danger",
};
const GridLadderCard: FC<GridLadderCardProps> = ({
  ladder,
  gridReturnPct,
  selected,
  onSelect,
  onClose,
  onDelete,
}) => {
  const navigate = useNavigate();
  const totalPnl = calculateGridPnl(ladder);
  const utilization = calculateGridUtilization(ladder);
  const isActive = isActiveGridLadder(ladder.status);
  const levelPnl = calculateLevelPnlSum(ladder);
  const closeAdjustmentPnl = calculateCloseAdjustmentPnl(ladder);
  const hasCloseAdjustment = Math.abs(closeAdjustmentPnl) >= 0.00005;
  const firstBreachAt = ladder.context.first_breach_at as
    number | null | undefined;
  const firstBreachUpAt = ladder.context.first_breach_up_at as
    number | null | undefined;
  const showAlgorithmName = ladder.algorithm_name !== "grid_ladder";
  return (
    <Card className={selected ? "selected-card" : ""} mb="md">
      <Box
        mb="sm"
        display="flex"
        style={{
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <div>
          <strong>{ladder.symbol}</strong>
          {(firstBreachAt != null || firstBreachUpAt != null) && (
            <Box
              display="flex"
              style={{
                flexWrap: "wrap",
                gap: 4,
              }}
              component="div"
            >
              {firstBreachAt != null && (
                <Badge
                  title={`Break-down breach started: ${new Date(firstBreachAt).toISOString()}`}
                  color="warning"
                  variant="light"
                >
                  ⚠ BREAK DOWN
                </Badge>
              )}
              {firstBreachUpAt != null && (
                <Badge
                  title={`Break-up breach started: ${new Date(firstBreachUpAt).toISOString()}`}
                  color="warning"
                  variant="light"
                >
                  ⚠ BREAK UP
                </Badge>
              )}
            </Box>
          )}
          {showAlgorithmName && (
            <Box c="dimmed" fz="xs" component="div">
              {ladder.algorithm_name}
            </Box>
          )}
        </div>
        <Box
          display="flex"
          style={{
            flexDirection: "column",
            alignItems: "flex-end",
            gap: 4,
          }}
          component="div"
        >
          <Badge color={returnBadgeBg(gridReturnPct)} variant="light">
            {gridReturnPct}%
          </Badge>
          <Badge color={statusColorMap[ladder.status]} variant="light">
            {ladder.status.toUpperCase()}
          </Badge>
        </Box>
      </Box>
      <Box>
        <Box fz="xs" c="dimmed" mb={8} component="div">
          {ladder.exchange} / {ladder.market_type}
        </Box>
        <Grid>
          <Grid.Col
            span={{
              base: 6,
            }}
          >
            Entry time
          </Grid.Col>
          <Grid.Col
            span={{
              base: 6,
            }}
            ta="right"
          >
            {formatTimestamp(ladder.created_at)}
          </Grid.Col>
        </Grid>
        <Grid>
          <Grid.Col
            span={{
              base: 6,
            }}
          >
            Range
          </Grid.Col>
          <Grid.Col
            span={{
              base: 6,
            }}
            ta="right"
          >
            {ladder.range_low} → {ladder.range_high}
          </Grid.Col>
        </Grid>
        <Grid>
          <Grid.Col
            span={{
              base: 6,
            }}
          >
            Breakout
          </Grid.Col>
          <Grid.Col
            span={{
              base: 6,
            }}
            ta="right"
          >
            {roundDecimals(ladder.breakout_low)} /{" "}
            {roundDecimals(ladder.breakout_high)}
          </Grid.Col>
        </Grid>
        <Grid>
          <Grid.Col
            span={{
              base: 6,
            }}
          >
            Levels
          </Grid.Col>
          <Grid.Col
            span={{
              base: 6,
            }}
            ta="right"
          >
            {ladder.level_count}
          </Grid.Col>
        </Grid>
        <Grid>
          <Grid.Col
            span={{
              base: 6,
            }}
          >
            Step
          </Grid.Col>
          <Grid.Col
            span={{
              base: 6,
            }}
            ta="right"
          >
            {roundDecimals(ladder.grid_step)}
          </Grid.Col>
        </Grid>
        <Grid>
          <Grid.Col
            span={{
              base: 6,
            }}
          >
            Margin
          </Grid.Col>
          <Grid.Col
            span={{
              base: 6,
            }}
            ta="right"
          >
            {roundDecimals(ladder.reserved_margin)} /{" "}
            {roundDecimals(ladder.total_margin)}
          </Grid.Col>
        </Grid>
        <Grid>
          <Grid.Col
            span={{
              base: 6,
            }}
          >
            Utilisation
          </Grid.Col>
          <Grid.Col
            span={{
              base: 6,
            }}
            ta="right"
          >
            {utilization.toFixed(2)}%
          </Grid.Col>
        </Grid>
        {isActive ? (
          <>
            <Grid>
              <Grid.Col
                span={{
                  base: 6,
                }}
              >
                TP cycled
              </Grid.Col>
              <Grid.Col
                className={`value-right ${levelPnl >= 0 ? "tone-success" : "tone-danger"}`}
                span={{
                  base: 6,
                }}
              >
                {levelPnl.toFixed(4)}
              </Grid.Col>
            </Grid>
            <Grid>
              <Grid.Col
                span={{
                  base: 6,
                }}
              >
                Unrealized
              </Grid.Col>
              <Grid.Col
                className={`value-right ${ladder.unrealized_pnl >= 0 ? "tone-success" : "tone-danger"}`}
                span={{
                  base: 6,
                }}
              >
                {ladder.unrealized_pnl.toFixed(4)}
              </Grid.Col>
            </Grid>
          </>
        ) : (
          <>
            {(levelPnl !== 0 || hasCloseAdjustment) && (
              <Grid>
                <Grid.Col
                  span={{
                    base: 6,
                  }}
                >
                  TP cycled
                </Grid.Col>
                <Grid.Col
                  className={`value-right ${levelPnl >= 0 ? "tone-success" : "tone-danger"}`}
                  span={{
                    base: 6,
                  }}
                >
                  {levelPnl.toFixed(4)}
                </Grid.Col>
              </Grid>
            )}
            {hasCloseAdjustment && (
              <Grid>
                <Grid.Col
                  span={{
                    base: 6,
                  }}
                >
                  Close adjustment
                </Grid.Col>
                <Grid.Col
                  className={`value-right ${closeAdjustmentPnl >= 0 ? "tone-success" : "tone-danger"}`}
                  span={{
                    base: 6,
                  }}
                >
                  {closeAdjustmentPnl.toFixed(4)}
                </Grid.Col>
              </Grid>
            )}
            {ladder.status === GridLadderStatus.CLOSED &&
              ladder.closed_at != null && (
                <Grid>
                  <Grid.Col
                    span={{
                      base: 6,
                    }}
                  >
                    Exit time
                  </Grid.Col>
                  <Grid.Col
                    span={{
                      base: 6,
                    }}
                    ta="right"
                  >
                    {formatTimestamp(ladder.closed_at)}
                  </Grid.Col>
                </Grid>
              )}
            <Grid>
              <Grid.Col
                span={{
                  base: 6,
                }}
              >
                Total realized
              </Grid.Col>
              <Grid.Col
                className={`value-right ${totalPnl >= 0 ? "tone-success" : "tone-danger"}`}
                span={{
                  base: 6,
                }}
              >
                {totalPnl.toFixed(4)}
              </Grid.Col>
            </Grid>
          </>
        )}
        <hr />
        <Box fz="xs" component="div">
          Open orders: {calculateOpenOrderCount(ladder)} · Filled levels:{" "}
          {calculateFilledLevelCount(ladder)}
        </Box>
        <Box
          display="flex"
          mt={8}
          style={{
            flexDirection: "column",
            gap: 4,
          }}
          component="div"
        >
          {ladder.levels.map((level, index) => {
            const isFilled = level.filled_entry_qty > 0;
            const tone =
              index < ladder.levels.length / 2
                ? "tone-danger"
                : index > ladder.levels.length / 2
                  ? "tone-success"
                  : "tone-muted";
            return (
              <div
                key={level.id}
                className={`ladder-level ${isFilled ? "ladder-level-filled" : ""}`}
              >
                <span className={tone}>
                  #{level.level_index} {level.side}
                </span>{" "}
                @ {level.price} · c:{level.contracts} · tp:
                {level.take_profit_price ?? "-"} · pnl:{level.realized_pnl}
              </div>
            );
          })}
        </Box>
      </Box>
      <Group
        mt="sm"
        display="flex"
        style={{
          justifyContent: "space-between",
        }}
      >
        <Button
          onClick={() => navigate(`/grid-ladders/${ladder.id}`)}
          color="info"
          type="button"
        >
          View details
        </Button>
        <Button
          onClick={() => onSelect(ladder.id)}
          color="warning"
          type="button"
        >
          {selected ? "Unselect" : "Select"}
        </Button>
        <Button onClick={() => onClose(ladder.id)} color="danger" type="button">
          Close ladder
        </Button>
        <Button
          onClick={() => onDelete(ladder.id)}
          variant="outline"
          color="danger"
          type="button"
        >
          Delete
        </Button>
      </Group>
    </Card>
  );
};
export default GridLadderCard;
