import React from "react";
import Plot from 'react-plotly.js';
import { Card, CardBody, CardHeader, CardTitle } from "reactstrap";

const generateOrders = (data, bot) => {

    let annotations = []
    let shapes = []
    let currentPrice, currentTime, takeProfitPrice, takeProfitTime;
    if (bot.active === "false") {
        // Match real base order price and time if active
        currentPrice = data.trace[0].close[data.trace[0].close.length - 1]
        currentTime = data.trace[0].x[data.trace[0].x.length - 1]

        // Match last order (last safety order triggered)
        takeProfitPrice = data.trace[0].close[data.trace[0].close.length - 1]
        takeProfitTime = data.trace[0].x[data.trace[0].x.length - 1]

    }
    // Base order
    const baseOrderA = {
        x: currentTime,
        y: currentPrice,
        xref: 'x',
        yref: 'y',
        text: 'Base order',
        font: { color:'DarkOrange' },
        showarrow: false,
        xanchor: 'left',
    }
    const baseOrderS = {
        type: 'line',
        xref: 'x',
        yref: 'y',
        x0: data.trace[0].x[0],
        y0: currentPrice,
        x1: currentTime,
        y1: currentPrice,
        line: {
            color: "DarkOrange",
            width: 4
        }
    }
    shapes.push(baseOrderS);
    annotations.push(baseOrderA);

    // Take profit order
    const price = (parseFloat(takeProfitPrice) + (parseFloat(takeProfitPrice) * (bot.take_profit / 100))).toFixed(process.env.REACT_APP_DECIMALS)
    const takeProfitA = {
        x: takeProfitTime,
        y: price,
        xref: 'x',
        yref: 'y',
        text: 'Take profit order',
        font: { color:'green' },
        showarrow: false,
        xanchor: 'left',
    }
    
    const takeProfitS = {
        type: 'line',
        xref: 'x',
        yref: 'y',
        x0: data.trace[0].x[0],
        y0: price,
        x1: takeProfitTime,
        y1: price,
        line: {
            color: "green",
            width: 4
        }
    }
    shapes.push(takeProfitS);
    annotations.push(takeProfitA);

    if (bot.trailling === "true") {
        // Take profit trailling order
        // Should replace the take profit order, that's why uses takeProfitTime
        const traillingPrice = (parseFloat(price) + (parseFloat(price) * (bot.take_profit / 100))).toFixed(process.env.REACT_APP_DECIMALS)
        const traillingA = {
            x: takeProfitTime,
            y: traillingPrice,
            xref: 'x',
            yref: 'y',
            text: 'Take profit order',
            font: { color:'green' },
            showarrow: false,
            xanchor: 'left',
        }
        const traillingS = {
            type: 'line',
            xref: 'x',
            yref: 'y',
            x0: takeProfitTime,
            y0: traillingPrice,
            x1: data.trace[0].x[150],
            y1: data.trace[0].close[0],
            line: {
                color: "green",
                width: 4
            }
        }
        shapes.push(traillingS);
        annotations.push(traillingA);
    }

    const maxSoCount = parseInt(bot.max_so_count)
    if (maxSoCount > 0) {
        let i = 0
        while (i < maxSoCount) {
            const price = (currentPrice - (currentPrice * (bot.price_deviation_so / 100))).toFixed(process.env.REACT_APP_DECIMALS)
            const safetyOrderA = {
                x: currentTime,
                y: price,
                xref: 'x',
                yref: 'y',
                text: `Safety order ${i}`,
                font: { color:'blue' },
                showarrow: false,
                xanchor: 'left',
            }
            const safetyOrderS = {
                x: currentTime,
                y: price,
                xref: 'x',
                yref: 'y',
                text: `Safety order ${i}`,
                font: { color:'blue' },
                showarrow: true,
                xanchor: 'left',
            }
            annotations.push(safetyOrderA);
            shapes.push(safetyOrderS);
    
        }
    }
    return {
        annotations: annotations,
        shapes: shapes
    };

}


function Candlestick({ title, data, bot }) {

    const { annotations, shapes } = generateOrders(data, bot);

    const layout = {
        dragmode: 'zoom',
        autosize: true,
        line_width: 50,
        margin: {
            r: 10,
            t: 25,
            b: 40,
            l: 60
        },
        showlegend: false,
        xaxis: {
            autorange: true,
            title: 'Date',
            type: 'date'
        },
        yaxis: {
            domain: [0, 1],
            tickformat: '.10f',
            type: 'linear',
            maxPoints: 50
        },
        annotations: annotations,
        shapes: shapes
    }

    return (
        <Card>
            <CardHeader>
                <CardTitle tag="h5">{title}</CardTitle>
            </CardHeader>
            <CardBody>
                <Plot
                    data={data.trace}
                    layout={layout}
                    useResizeHandler={true}
                    style={{ "width": "100%", "height": "100%" }}
                />
            </CardBody>
        </Card>

    );
}

export default Candlestick;