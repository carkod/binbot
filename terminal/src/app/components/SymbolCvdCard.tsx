import { useCvdSymbolQuery } from "../../features/marketApiSlice";
import StoredCvdCard from "./StoredCvdCard";

const SymbolCvdCard = ({
  symbol,
  enabled,
}: {
  symbol: string;
  enabled: boolean;
}) => {
  const { currentData, isFetching, isError } = useCvdSymbolQuery(symbol, {
    skip: !enabled || !symbol,
    pollingInterval: 30_000,
    refetchOnMountOrArgChange: true,
    refetchOnFocus: true,
    refetchOnReconnect: true,
  });
  if (!enabled || !symbol) {
    return <p>Enter a symbol</p>;
  }
  return (
    <StoredCvdCard
      symbol={symbol}
      result={currentData}
      isLoading={!currentData && isFetching}
      isError={isError}
    />
  );
};

export default SymbolCvdCard;
