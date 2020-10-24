import React , { useState, useEffect } from "react";
import { Card, CardBody, CardHeader, CardTitle, Table, Pagination, PaginationItem, PaginationLink, Col, Row } from "reactstrap";

function CardTable({ title, data, pages, limit, offset, loadPage }) {

    const [pageSize, setpageSize] = useState(10);
    const [totalPages, setTotalPages] = useState(1);
    const [displayedPages, setdisplayedPages] = useState([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, "..."]);
    const [currentPage, setCurrentPage] = useState(1);

    useEffect(() => {
        getTotalPages(pages, limit);
        
    }, [pages, limit]);

    const getTotalPages = (pages, limit) => {
        const totalPages = Math.ceil(pages / limit);
        setTotalPages(totalPages);
    }

    const goToPage = (num) => {
        setCurrentPage(num);
        const newOffset = (num - 1)  * pageSize;
        loadPage(limit, newOffset);
    }

    const nextPage = () => {
        if (currentPage < totalPages) {
            const newCurrentPage = currentPage + 1
            const newOffset = (newCurrentPage - 1)  * pageSize;
            setCurrentPage(newCurrentPage);
            let newPageList = displayedPages.slice(1, displayedPages.length - 2);
            const lastNumberList = newPageList[newPageList.length - 1];
            let newPageList2 = newPageList.concat(lastNumberList + 1);
            newPageList2.concat("...");
            setdisplayedPages(newPageList2);
            loadPage(limit, newOffset);
        }
    }
    
    const previousPage = () => {
        if (currentPage > 1) {
            const newCurrentPage = currentPage - 1
            setCurrentPage(newCurrentPage);
            const newOffset = (newCurrentPage - 1)  * pageSize;
            let newPageList = displayedPages.slice(1);
            const newFirstElement = newPageList[0] - 1;
            newFirstElement.concat(displayedPages);
            newPageList.concat("...");
            setdisplayedPages(newPageList);
            loadPage(limit, newOffset);
        }
    }
        
    const firstPage = () => {
        const newCurrentPage = 1
        setCurrentPage(newCurrentPage);
        const newOffset = (newCurrentPage - 1)  * pageSize;
        loadPage(limit, newOffset);
    }

    const lastPage = () => {
        const newCurrentPage = totalPages;
        setCurrentPage(newCurrentPage);
        const newOffset = (newCurrentPage - 1)  * pageSize;
        loadPage(limit, newOffset);
    }

    return (
        <Card>
            <CardHeader>
                <CardTitle tag="h4">{title}</CardTitle>
            </CardHeader>
            <CardBody>
                <Table responsive>
                    <thead className="text-primary">
                        <tr>
                            <th>Date</th>
                            <th>Symbol</th>
                            <th>Side</th>
                            <th>Type</th>
                            <th className="text-right">Price</th>
                            <th className="text-right">Original Quantity</th>
                            <th className="text-right">Executed Quantity</th>
                        </tr>
                    </thead>
                    <tbody>
                        {data && data.map(x =>
                            <tr key={x._id.$oid}>
                                <td>{new Date(x.updateTime).toLocaleDateString('en-gb', { year: 'numeric', month: 'long', day: 'numeric' })}</td>
                                <td>{x.symbol}</td>
                                <td>{x.side}</td>
                                <td>{x.type}</td>
                                <td className="text-right">{x.price}</td>
                                <td className="text-right">{x.origQty}</td>
                                <td className="text-right">{x.executedQty}</td>
                            </tr>
                        )}


                    </tbody>
                </Table>
                <Row>
                    <Col sm="12" md={{ size: 6, offset: 4 }} >
                        <Pagination aria-label="Page navigation example">
                            <PaginationItem>
                                <PaginationLink first href="#" onClick={firstPage} />
                            </PaginationItem>
                            <PaginationItem>
                                <PaginationLink previous href="#" onClick={previousPage} />
                            </PaginationItem>

                            {displayedPages && displayedPages.map((x,i) => (
                                <PaginationItem key={i} active={currentPage === x}>
                                    {x === "..." ? <span className="page-link">{x}</span> : 
                                        <PaginationLink href="#" onClick={() => goToPage(x)}>
                                            {x}
                                        </PaginationLink>
                                    }
                                </PaginationItem>
                                )
                            )}
                            
                            <PaginationItem>
                                <PaginationLink next href="#" onClick={nextPage} />
                            </PaginationItem>
                            <PaginationItem>
                                <PaginationLink last href="#" onClick={lastPage}/>
                            </PaginationItem>
                        </Pagination>
                    </Col>
                </Row>
            </CardBody>
        </Card>

    );
}

export default CardTable;
