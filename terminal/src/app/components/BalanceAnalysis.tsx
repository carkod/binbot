import { formGridBreakpoints } from "../../theme";
import { Box, Card, Grid, Title } from "@mantine/core";
import { type FC } from "react";
import { type BalanceData } from "../../features/features.types";
import { type MarketType } from "../../utils/enums";
import { roundDecimals } from "../../utils/math";
import { useRiskBeta } from "../hooks/useRiskBeta";
const BalanceAnalysis: FC<{
  accountData: BalanceData;
  marketType: MarketType;
}> = ({ accountData, marketType }) => {
  const { beta, isLoading: loadingBeta } = useRiskBeta(accountData, marketType);
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
        <Grid type="container" breakpoints={formGridBreakpoints} mb="lg">
          <Grid.Col span={{ base: 12, md: 8 }}>Available fiat</Grid.Col>
          <Grid.Col span={{ base: 12, md: 4 }}>
            <Box c="primary.8" component="div">
              <strong>{`${
                accountData.fiat_available > 0
                  ? roundDecimals(accountData.fiat_available, 6)
                  : 0
              } ${accountData.fiat_currency}`}</strong>
            </Box>
          </Grid.Col>
        </Grid>
        <Grid type="container" breakpoints={formGridBreakpoints} mb="lg">
          <Grid.Col span={{ base: 12, md: 8 }}>Total fiat value</Grid.Col>
          <Grid.Col span={{ base: 12, md: 4 }}>
            <Box c="primary.8" component="div">
              <strong>{`${
                accountData?.estimated_total_fiat > 0
                  ? accountData.estimated_total_fiat.toFixed(2)
                  : 0
              } ${accountData.fiat_currency}`}</strong>
            </Box>
          </Grid.Col>
        </Grid>
        <Grid type="container" breakpoints={formGridBreakpoints} mb="lg">
          <Grid.Col span={{ base: 12, md: 8 }}>Risk beta (BTC)</Grid.Col>
          <Grid.Col span={{ base: 12, md: 4 }}>
            <Box c="primary.8" component="div">
              <strong>
                {loadingBeta
                  ? "Calculating..."
                  : beta === null
                    ? "—"
                    : beta.toFixed(2)}
              </strong>
            </Box>
          </Grid.Col>
        </Grid>
        <Grid type="container" breakpoints={formGridBreakpoints}>
          <Grid.Col span={{ base: 12, md: 8 }}>
            Portfolio of assets
            <br />
            (actual)
          </Grid.Col>
          <Grid.Col span={{ base: 12, md: 4 }}>
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
