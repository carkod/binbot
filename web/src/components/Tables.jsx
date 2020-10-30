import React, { useState, useEffect } from "react";
import { Card, CardBody, CardHeader, CardTitle, Table, Pagination, PaginationItem, PaginationLink, Col, Row } from "reactstrap";

function Tables({ title, data, pages, limit = 10, loadPage }) {

  const [totalPages, setTotalPages] = useState(1);
  const [displayedPages, setdisplayedPages] = useState([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, "..."]);
  const [currentPage, setCurrentPage] = useState(1);
  const [firstNavigationDisabled, setFirstNavigationDisabled] = useState(true);
  const [lastNavigationDisabled, setLastNavigationDisabled] = useState(false);


  useEffect(() => {
    getTotalPages(pages, limit);

  }, [pages, limit]);

  const getTotalPages = (pages, limit) => {
    const totalPages = Math.ceil(pages / limit);
    setTotalPages(totalPages);
  }

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
    loadPage(limit, newOffset);
  }

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
      loadPage(limit, newOffset);
    }
  }

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
      loadPage(limit, newOffset);
    }
  }

  const firstPage = () => {
    const newCurrentPage = 1
    setCurrentPage(newCurrentPage);
    const newOffset = (newCurrentPage - 1) * limit;
    loadPage(limit, newOffset);
  }

  const lastPage = () => {
    const newCurrentPage = totalPages;
    setCurrentPage(newCurrentPage);
    const newOffset = (newCurrentPage - 1) * limit;
    loadPage(limit, newOffset);
  }

  const expandPages = () => {
    // Not greater or equal than totalPages length
    if (displayedPages[displayedPages.length - 2] <= totalPages) {
      let newPageList = displayedPages.slice(1, displayedPages.length - 1);
      const lastNumberList = newPageList[newPageList.length - 1];
      let newPageList2 = newPageList.concat(lastNumberList + 1);
      const newPageList3 = newPageList2.concat("...");
      setdisplayedPages(newPageList3);
    } else {
      setLastNavigationDisabled(true)
    }
  }

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
      setFirstNavigationDisabled(true)
    }
  }

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
  }

  return (
    <>
      <div className="content">
        <Row>
          <Col md="12">
            <Card className="card-plain">
              <CardHeader>
                <CardTitle tag="h4">{title}</CardTitle>
                <p className="card-category">
                  Here is a subtitle for this table
                  </p>
              </CardHeader>
              <CardBody>
                <Table responsive>
                  <thead className="text-primary">
                    <tr>
                      <th>Name</th>
                      <th>Country</th>
                      <th>City</th>
                      <th className="text-right">Salary</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td>Dakota Rice</td>
                      <td>Niger</td>
                      <td>Oud-Turnhout</td>
                      <td className="text-right">$36,738</td>
                    </tr>
                    <tr>
                      <td>Minerva Hooper</td>
                      <td>Curaçao</td>
                      <td>Sinaai-Waas</td>
                      <td className="text-right">$23,789</td>
                    </tr>
                    <tr>
                      <td>Sage Rodriguez</td>
                      <td>Netherlands</td>
                      <td>Baileux</td>
                      <td className="text-right">$56,142</td>
                    </tr>
                    <tr>
                      <td>Philip Chaney</td>
                      <td>Korea, South</td>
                      <td>Overland Park</td>
                      <td className="text-right">$38,735</td>
                    </tr>
                    <tr>
                      <td>Doris Greene</td>
                      <td>Malawi</td>
                      <td>Feldkirchen in Kärnten</td>
                      <td className="text-right">$63,542</td>
                    </tr>
                    <tr>
                      <td>Mason Porter</td>
                      <td>Chile</td>
                      <td>Gloucester</td>
                      <td className="text-right">$78,615</td>
                    </tr>
                    <tr>
                      <td>Jon Porter</td>
                      <td>Portugal</td>
                      <td>Gloucester</td>
                      <td className="text-right">$98,615</td>
                    </tr>
                  </tbody>
                </Table>
                <Row>
                  <Col md="12" >
                    <Pagination aria-label="Page navigation example">
                      <PaginationItem disabled={firstNavigationDisabled}>
                        <PaginationLink first href="#" onClick={firstPage} />
                      </PaginationItem>
                      <PaginationItem disabled={firstNavigationDisabled} >
                        <PaginationLink previous href="#" onClick={previousPage} />
                      </PaginationItem>

                      {displayedPages && displayedPages.map((x, i) => (
                        <PaginationItem key={i} active={currentPage === x}>
                          {x === "..." ? <span className="page-link">{x}</span> :
                            <PaginationLink href="#" onClick={() => goToPage(x)}>
                              {x}
                            </PaginationLink>
                          }
                        </PaginationItem>
                      )
                      )}

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
          </Col>
        </Row>
      </div>
    </>
  );
}

export default Tables;
