import { Alert, Grid } from "@mantine/core";
import { getApiErrorMessage } from "../../utils/api";
import { useMicrostructureData } from "../hooks/useMicrostructureData";
import SpreadAndDepthCard from "./SpreadAndDepthCard";
import SymbolCvdCard from "./SymbolCvdCard";
const OrderBookAnalysis = ({
  enabled,
  showError = false,
}: {
  enabled: boolean;
  showError?: boolean;
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
      <Grid>
        <Grid.Col
          span={{
            base: 12,
            md: 6,
          }}
        >
          <SpreadAndDepthCard
            orderBookHistory={orderBookHistory}
            enabled={enabled}
            isFetching={isFetching}
            isError={isError}
            onRetry={() => refetch()}
          />
        </Grid.Col>
        <Grid.Col
          span={{
            base: 12,
            md: 6,
          }}
        >
          <SymbolCvdCard symbol={symbol} enabled={enabled} />
        </Grid.Col>
      </Grid>
    </>
  );
};
export default OrderBookAnalysis;
