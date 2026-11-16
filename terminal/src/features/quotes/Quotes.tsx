import { Alert, Blockquote, Loader, NativeSelect, Stack } from "@mantine/core";
import { useState } from "react";
import { useGetQuotesQuery } from "./quotesApiSlice";
const options = [5, 10, 20, 30];
export const Quotes = () => {
  const [numberOfQuotes, setNumberOfQuotes] = useState(10);
  // Using a query hook automatically fetches data and returns query values
  const { data, isError, isLoading, isSuccess } =
    useGetQuotesQuery(numberOfQuotes);
  if (isError) {
    return <Alert color="danger" title="Unable to load quotes" />;
  }
  if (isLoading) {
    return <Loader aria-label="Loading quotes" />;
  }
  if (isSuccess) {
    return (
      <Stack>
        <NativeSelect
          label="Select the quantity of quotes to fetch"
          value={numberOfQuotes}
          onChange={(e) => {
            setNumberOfQuotes(Number(e.target.value));
          }}
        >
          {options.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </NativeSelect>
        {data.quotes.map(({ author, quote, id }) => (
          <Blockquote key={id} cite={author}>
            &ldquo;{quote}&rdquo;
          </Blockquote>
        ))}
      </Stack>
    );
  }
  return null;
};
