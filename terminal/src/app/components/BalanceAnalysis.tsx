import { Box, Card, Grid, Title, Tooltip } from "@mantine/core";
import { type FC } from "react";
import { selectBot } from "../../features/bots/botSlice";
import { type BalanceData } from "../../features/features.types";
import { roundDecimals } from "../../utils/math";
import { useAppSelector } from "../hooks";
import { useRiskBeta } from "../hooks/useRiskBeta";

const BalanceAnalysis: FC<{
  accountData: BalanceData;
}> = ({ accountData }) => {
  const { bot } = useAppSelector(selectBot);

  const { beta, isLoading: loadingBeta } = useRiskBeta(
    bot.pair,
    bot.market_type,
  );

  return (
    <Card mb="md">
      <Box
        mb="sm"
        display="flex"
        style={{
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <Title order={5}>Account breakdown</Title>
      </Box>
      <Box>
        <Grid mb="lg">
          <Grid.Col span={6}>Available fiat</Grid.Col>
          <Grid.Col span={6} ta="right">
            <Box c="primary.8" component="div">
              <strong>{`${
                accountData.fiat_available > 0
                  ? roundDecimals(accountData.fiat_available, 6)
                  : 0
              } ${accountData.fiat_currency}`}</strong>
            </Box>
          </Grid.Col>
        </Grid>
        <Grid mb="lg">
          <Grid.Col span={6}>Total fiat value</Grid.Col>
          <Grid.Col span={6} ta="right">
            <Box c="primary.8" component="div">
              <strong>{`${
                accountData?.estimated_total_fiat > 0
                  ? accountData.estimated_total_fiat.toFixed(2)
                  : 0
              } ${accountData.fiat_currency}`}</strong>
            </Box>
          </Grid.Col>
        </Grid>
        <Grid mb="lg">
          <Grid.Col span={6}>
            <Tooltip
              label={`${bot.pair || "Selected symbol"} sensitivity to BTC, using completed 15-minute returns over the past 24 hours.`}
              multiline
              w={280}
            >
              <span>Symbol risk beta (BTC)</span>
            </Tooltip>
          </Grid.Col>
          <Grid.Col span={6} ta="right">
            <Box c="primary.8" component="div">
              <strong>
                {loadingBeta
                  ? "Calculating..."
                  : beta === null
                    ? "Unavailable"
                    : beta.toFixed(2)}
              </strong>
            </Box>
          </Grid.Col>
        </Grid>
        <Grid>
          <Grid.Col span={6}>
            Portfolio of assets
            <br />
            (actual)
          </Grid.Col>
          <Grid.Col span={6} ta="right">
            {Object.entries(accountData.balances).map(([asset, amount], i) => (
              <Box key={i} c="primary.8" component="div">
                <strong>{`${amount} ${asset}`}</strong>
              </Box>
            ))}
          </Grid.Col>
        </Grid>
      </Box>
    </Card>
  );
};

export default BalanceAnalysis;
