import { Grid } from "@mantine/core";
import { type FC } from "react";
const NotFound: FC = () => {
  return (
    <div className="content">
      <Grid>
        <Grid.Col
          span={{
            base: 12,
            md: 12,
          }}
        >
          Page not found.
        </Grid.Col>
      </Grid>
    </div>
  );
};
export default NotFound;
