import { type FC } from 'react';
import { Col, Container, Form, Row } from 'react-bootstrap';

const BotsDateFilter: FC<{
    selectedDate: string;
    handleDateChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
}> = ({ selectedDate, handleDateChange }) => {

  return (
    <Container>
      <Row className="justify-content-md-center">
        <Col md="auto">
          <Form>
            <Form.Group controlId="formDate">
              <Form.Label>Filter by date</Form.Label>
              <Form.Control 
                type="date" 
                value={selectedDate} 
                onChange={handleDateChange} 
              />
            </Form.Group>
          </Form>
          {selectedDate && (
            <div className="mt-3">
              <h5>Selected Date: {selectedDate}</h5>
            </div>
          )}
        </Col>
      </Row>
    </Container>
  );
};

export default BotsDateFilter;