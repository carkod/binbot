import { type FC } from "react";
import { Card, Spinner } from "react-bootstrap";

type CardLoadingSpinnerProps = {
  label: string;
  className?: string;
};

const CardLoadingSpinner: FC<CardLoadingSpinnerProps> = ({
  label,
  className,
}) => (
  <Card className={className}>
    <Card.Body className="d-flex justify-content-center align-items-center py-5">
      <Spinner
        animation="border"
        variant="warning"
        role="status"
        aria-label={`Loading ${label}...`}
      >
        <span className="visually-hidden">Loading {label}...</span>
      </Spinner>
    </Card.Body>
  </Card>
);

export default CardLoadingSpinner;
