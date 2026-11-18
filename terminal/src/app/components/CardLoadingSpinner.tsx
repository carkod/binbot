import { Card, Center, Loader } from "@mantine/core";

const CardLoadingSpinner = ({
  label,
  className,
}: {
  label: string;
  className?: string;
}) => (
  <Card className={`card-loading ${className ?? ""}`.trim()} mb="md">
    <Center mih="inherit" h="100%" py="xl">
      <Loader
        color="warning"
        role="status"
        aria-label={`Loading ${label}...`}
      />
    </Center>
  </Card>
);

export default CardLoadingSpinner;
