import { Card, Col, Container, Row } from "react-bootstrap"
import { Line } from "react-chartjs-2"
import { listCssColors } from "../../utils/validations"
import { type ChartOptions } from "chart.js"
import 'chart.js/auto'; // ADD THIS


const PortfolioBenchmarkChart = ({ chartData }) => {
  const lastUsdt = chartData.usdcSeries?.[chartData.usdcSeries.length - 1]
  const lastBtc = chartData.btcSeries?.[chartData.btcSeries.length - 1]

  const PBOptions: ChartOptions = {
		title: {
			text: "chart.js",
			display: true,
		},
		tooltips: {
			enabled: true,
			intersect: true,
			mode: "index",
			position: "nearest",
			callbacks: {
				label: (item, d) => {
				  const value = d.datasets[item.datasetIndex].data[item.index].y
				  return `${d.datasets[item.datasetIndex].label} ${value}`
				},
				title: (items, d) => {
					const item0 = items[0]
					return d.datasets[item0.datasetIndex].data[item0.index]["x"].format(
						"MM-DD HH:mm",
					)
				},
				labelColor: (item, chart) => ({
					borderColor: chart.data.datasets[item.datasetIndex].backgroundColor.toString(),
					backgroundColor: chart.data.datasets[item.datasetIndex].borderColor.toString(),
				}),
			},
		},
		maintainAspectRatio: false,
		legend: {
			display: true,
			position: "bottom",
		},
		scales: {
			// xAxes: [
			// 	{
			// 		type: "time",
			// 		time: {
			// 			unit: "hour",
			// 			minUnit: "hour",
			// 			unitStepSize: 1,
			// 			displayFormats: {
			// 				hour: "HH[h]",
			// 			},
			// 		},
			// 		gridLines: {
			// 			drawOnChartArea: false,
			// 		},
			// 	},
			// ],
			// yAxes: [],
		},
		elements: {
			point: {
				radius: 0,
				hitRadius: 10,
				hoverRadius: 4,
				hoverBorderWidth: 3,
			},
		},
	}

  const data = {
    labels: chartData.datesSeries,
    datasets:[
      {
        label: 'Portfolio in USDCSeries',
        data: chartData.usdcSeriesSeries,
        backgroundColor: listCssColors[0],
      },
      {
        label: 'BTC prices',
        data: chartData.btcSeries,
        backgroundColor: listCssColors[1],
      }
    ],
  }

  return (
    <Card className="card-chart">
      <Card.Header>
        <Container>
          <Row>
            <Col lg="1" md="1" sm="1">
              <div className="u-fa-lg">
                <i
                  className={`fa fa-suitcase ${lastUsdt > lastBtc ? "text-success" : lastUsdt < lastBtc ? "text-danger" : ""}`}
                />
              </div>
            </Col>
            <Col lg="11" md="11" sm="11">
              <Card.Title as="h5">Portfolio benchmarking</Card.Title>
              <div>
                <p className="card-category u-text-left">
                  Compare portfolio against BTC.
                  <br />
                  Values in % difference
                </p>
              </div>
            </Col>
          </Row>
        </Container>
      </Card.Header>
      <Card.Body>
        <Line data={data} options={PBOptions} />
      </Card.Body>
      <Card.Footer>
        {/* <div className="legend">
          {legend &&
            legend.map((x, i) => {
              return (
                <span key={i} className="u-legend-text">
                  <i className="fa fa-circle" style={{ color: x.color }} />
                  {x.name}
                </span>
              )
            })}
        </div> */}
        <hr />
        {chartData.dates && (
          <div className="card-stats">
            <i className="fa fa-check" /> Last updated{" "}
            {chartData.dates[chartData.dates.length - 1]}
          </div>
        )}
      </Card.Footer>
    </Card>
  )
}

export default PortfolioBenchmarkChart
