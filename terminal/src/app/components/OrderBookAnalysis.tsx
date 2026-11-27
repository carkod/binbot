import { Alert, Grid, SimpleGrid } from "@mantine/core";
import { getApiErrorMessage } from "../../utils/api";
import { useMicrostructureData } from "../hooks/useMicrostructureData";
import SpreadAndDepthCard from "./SpreadAndDepthCard";
import SymbolCvdCard from "./SymbolCvdCard";
import SymbolTradesCard from "./SymbolTradesCard";

const OrderBookAnalysis = ({
  enabled,
  showError = false,
  depthWindowMinutes,
}: {
  enabled: boolean;
  showError?: boolean;
  depthWindowMinutes?: number;
}) => {
  const { symbol, liquidity, orderBookHistory } = useMicrostructureData();

  const { isFetching, isError, error, refetch } = liquidity;

  return (
    <>
      {enabled && showError && isError && (
        <Alert color="danger">
          {getApiErrorMessage(error, "KuCoin symbol request failed")}
        </Alert>
      )}
      <SimpleGrid cols={{ base: 1, md: 2 }}>
        <SpreadAndDepthCard
          depthWindowMinutes={depthWindowMinutes}
          orderBookHistory={orderBookHistory}
          enabled={enabled}
          isFetching={isFetching}
          isError={isError}
          onRetry={() => refetch()}
        />
        <SymbolCvdCard symbol={symbol} enabled={enabled} />
      </SimpleGrid>
      <Grid mt="md">
        <Grid.Col span={{ base: 12, md: 6 }}>
          <SymbolTradesCard symbol={symbol} enabled={enabled} />
        </Grid.Col>
      </Grid>
    </>
  );
};

export default OrderBookAnalysis;
