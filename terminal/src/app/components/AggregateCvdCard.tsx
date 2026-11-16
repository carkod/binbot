import { useCvdAggregateQuery } from "../../features/marketApiSlice";
import StoredCvdCard from "./StoredCvdCard";
const AggregateCvdCard = () => {
  const {
    data: result,
    isLoading,
    isError,
  } = useCvdAggregateQuery(undefined, {
    pollingInterval: 60000,
  });
  return (
    <StoredCvdCard result={result} isLoading={isLoading} isError={isError} />
  );
};
export default AggregateCvdCard;
