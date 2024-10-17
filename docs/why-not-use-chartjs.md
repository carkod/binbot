After doing a test with Chart.js for the portfolio benchmark line chart, still preferred plotly.
- The graphs are already built with Plotly
- The system used by Chart.js isn't too different from Plotly, Chart.js itself is imperative JS code, so if you don't want to create instances and handle rendering, you can install the `react-chartjs-2` library, but then you bump into other issues, like different props passed (with Chart.js you use only config, while the react component library separtes `data` and `options` as 2 separate props), no different from Plotly.
- Options are all very similar, no clear benefit in switching
- Another big issue, is that for Chart.js if you want to support some features such as labelling on top of bar charts, you need to install and enable plug ins, which you don't have to with Plotly.
- The only big benefit I see from Chart.js is that you get animations by default, no plugins needed. Plotly doesn't support any animations out of the box.
