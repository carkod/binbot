import React from "react";
import Plot from 'react-plotly.js';

function PieChart({ data }) {

    const layout = {
        // autosize: true,
        // line_width: 50,
        margin: {
            r: 5,
            t: 5,
            b: 10,
            l: 10,
        },
        height: 350,
        width: 250,
        legend: {
            orientation: "h",
            // yanchor: "bottom",
            // xanchor: "left",
            // y: -0.2,
            // x: 0.2
        }
    }

    return (
        <>
            <Plot
                data={data}
                layout={layout}
                // useResizeHandler={true}
                // style={{ "width": "100%", "height": "100%" }}
            />
        </>

    );
}

export default PieChart;