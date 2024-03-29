import React, { useEffect, useState } from "react";
import {
  Card,
  CardBody,
  CardHeader,
  CardTitle,
  Col,
  Input,
  Label,
  Pagination,
  PaginationItem,
  PaginationLink,
  Row,
  Table,
} from "reactstrap";

function CardTable({
  title,
  data,
  pages,
  limit = 10,
  loadPage,
  updateData,
  filter,
}) {
  const [totalPages, setTotalPages] = useState(1);
  const [displayedPages, setdisplayedPages] = useState([
    1,
    2,
    3,
    4,
    5,
    6,
    7,
    8,
    9,
    10,
    11,
    12,
    13,
    14,
    15,
    16,
    17,
    18,
    19,
    20,
    21,
    22,
    23,
    24,
    25,
    26,
    "...",
  ]);
  const [currentPage, setCurrentPage] = useState(1);
  const [status] = useState("FILLED");
  const [firstNavigationDisabled, setFirstNavigationDisabled] = useState(true);
  const [lastNavigationDisabled, setLastNavigationDisabled] = useState(false);

  useEffect(() => {
    getTotalPages(pages, limit);
  }, [pages, limit]);

  const getTotalPages = (pages, limit) => {
    const totalPages = Math.ceil(pages / limit);
    setTotalPages(totalPages);
  };

  const goToPage = (num) => {
    navigationDisabilityChecks(num);
    setCurrentPage(num);
    const newOffset = (num - 1) * limit;
    if (num === displayedPages[displayedPages.length - 2]) {
      expandPages();
    }
    if (num === displayedPages[0]) {
      retractPages();
    }
    loadPage(limit, newOffset, status);
  };

  const nextPage = () => {
    if (currentPage < totalPages) {
      const newCurrentPage = currentPage + 1;
      navigationDisabilityChecks(newCurrentPage);
      const newOffset = (newCurrentPage - 1) * limit;
      setCurrentPage(newCurrentPage);
      if (newCurrentPage === displayedPages[displayedPages.length - 2]) {
        expandPages();
      }
      if (newCurrentPage === displayedPages[0]) {
        retractPages();
      }
      loadPage(limit, newOffset, status);
    }
  };

  const previousPage = () => {
    if (currentPage > 1) {
      const newCurrentPage = currentPage - 1;
      navigationDisabilityChecks(newCurrentPage);
      setCurrentPage(newCurrentPage);
      const newOffset = (newCurrentPage - 1) * limit;
      if (newCurrentPage === displayedPages[displayedPages.length - 2]) {
        expandPages();
      }
      if (newCurrentPage === displayedPages[0]) {
        retractPages();
      }
      loadPage(limit, newOffset, status);
    }
  };

  const firstPage = () => {
    const newCurrentPage = 1;
    setCurrentPage(newCurrentPage);
    const newOffset = (newCurrentPage - 1) * limit;
    loadPage(limit, newOffset, status);
  };

  const lastPage = () => {
    const newCurrentPage = totalPages;
    setCurrentPage(newCurrentPage);
    const newOffset = (newCurrentPage - 1) * limit;
    loadPage(limit, newOffset, status);
  };

  const expandPages = () => {
    // Not greater or equal than totalPages length
    if (displayedPages[displayedPages.length - 2] <= totalPages) {
      let newPageList = displayedPages.slice(1, displayedPages.length - 1);
      const lastNumberList = newPageList[newPageList.length - 1];
      let newPageList2 = newPageList.concat(lastNumberList + 1);
      const newPageList3 = newPageList2.concat("...");
      setdisplayedPages(newPageList3);
    } else {
      setLastNavigationDisabled(true);
    }
  };

  const retractPages = () => {
    // Not less or equal than 1
    if (displayedPages[0] > 1) {
      const newPageList1 = displayedPages.slice(0, displayedPages.length - 2);
      const newFirstElement = [newPageList1[0] - 1];
      const newPageList2 = newFirstElement.concat(newPageList1);
      const newPageList3 = newPageList2.concat("...");
      setdisplayedPages(newPageList3);
    }
    if (displayedPages[0] === 1) {
      setFirstNavigationDisabled(true);
    }
  };

  const navigationDisabilityChecks = (num) => {
    if (num > 1 && firstNavigationDisabled) {
      setFirstNavigationDisabled(false);
    }
    if (num === 1 && !firstNavigationDisabled) {
      setFirstNavigationDisabled(true);
    }
    if (num < totalPages && lastNavigationDisabled) {
      setLastNavigationDisabled(false);
    }
    if (num === totalPages && !lastNavigationDisabled) {
      setLastNavigationDisabled(true);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle tag="h4">
          <span>{title}</span>
        </CardTitle>
        <Label for="status">Status filter</Label>
        <Input
          type="select"
          name="status"
          id="status"
          onChange={(e) => filter(e)}
          defaultValue={status}
        >
          <option value="FILLED">Filled</option>
          <option value="CANCELED">Canceled</option>
          <option value="">All</option>
        </Input>
      </CardHeader>
      <CardBody>
        <Table>
          <thead className="text-primary">
            <tr>
              <th>Date</th>
              <th>Symbol</th>
              <th>Side</th>
              <th>Type</th>
              <th>Status</th>
              <th className="text-right">Price</th>
              <th className="text-right">Quantity</th>
              <th className="text-right">Total</th>
            </tr>
          </thead>
          <tbody>
            {data &&
              data.map((x) => (
                <tr key={x.id}>
                  <td>
                    {new Date(x.updateTime).toLocaleDateString("en-gb", {
                      year: "numeric",
                      month: "long",
                      day: "numeric",
                    })}
                  </td>
                  <td>{x.symbol}</td>
                  <td>{x.side}</td>
                  <td>{x.type}</td>
                  <td>{x.status}</td>
                  <td className="text-right">{parseFloat(x.price)}</td>
                  <td className="text-right">{parseFloat(x.executedQty)}</td>
                  <td className="text-right">
                    {parseFloat(x.price * x.executedQty)}
                  </td>
                </tr>
              ))}
          </tbody>
        </Table>
        <Row>
          <Col md="12">
            <Pagination aria-label="Page navigation example">
              <PaginationItem disabled={firstNavigationDisabled}>
                <PaginationLink first href="#" onClick={firstPage} />
              </PaginationItem>
              <PaginationItem disabled={firstNavigationDisabled}>
                <PaginationLink previous href="#" onClick={previousPage} />
              </PaginationItem>

              {displayedPages &&
                displayedPages.map((x, i) => (
                  <PaginationItem key={i} active={currentPage === x}>
                    {x === "..." ? (
                      <span className="page-link">{x}</span>
                    ) : (
                      <PaginationLink href="#" onClick={() => goToPage(x)}>
                        {x}
                      </PaginationLink>
                    )}
                  </PaginationItem>
                ))}

              <PaginationItem disabled={lastNavigationDisabled}>
                <PaginationLink next href="#" onClick={nextPage} />
              </PaginationItem>
              <PaginationItem disabled={lastNavigationDisabled}>
                <PaginationLink last href="#" onClick={lastPage} />
              </PaginationItem>
            </Pagination>
          </Col>
        </Row>
      </CardBody>
    </Card>
  );
}

export default CardTable;
