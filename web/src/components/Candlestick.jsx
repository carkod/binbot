import React from "react";
import Plot from 'react-plotly.js';
import { Card, CardBody, CardHeader, CardTitle } from "reactstrap";

function Candlestick({ title, data }) {

    return (
        <Card>
            <CardHeader>
                <CardTitle tag="h5">{title}</CardTitle>
            </CardHeader>
            <CardBody>
                <Plot
                    data={data.trace}
                    layout={data.layout}
                    useResizeHandler={true}
                    style={{"width": "100%", "height": "100%"}}
                />
            </CardBody>
        </Card>

    );
}

export default Candlestick;