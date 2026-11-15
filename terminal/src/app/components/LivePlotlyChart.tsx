import { memo, useMemo } from "react";
import { motion } from "motion/react";
import { chartRevealVariants, liveChartTransition } from "../../utils/motion";
import PlotlyChart from "./PlotlyChart";

interface LivePlotlyChartProps {
  data: Record<string, unknown>[];
  layout: Record<string, unknown>;
}

const config = { responsive: true, displayModeBar: false };
const style = { width: "100%", height: "100%" };

const LivePlotlyChart = memo(function LivePlotlyChart({
  data,
  layout,
}: LivePlotlyChartProps) {
  const animatedLayout = useMemo(
    () => ({
      ...layout,
      // Preserve legend selections as fresh observations arrive. Explicit time
      // ranges still advance the live window on order-book charts.
      uirevision: "microstructure",
      transition: liveChartTransition,
    }),
    [layout],
  );

  return (
    <motion.div
      initial="hidden"
      animate="visible"
      variants={chartRevealVariants}
    >
      <PlotlyChart
        data={data}
        layout={animatedLayout}
        config={config}
        style={style}
        useResizeHandler={true}
      />
    </motion.div>
  );
});

export default LivePlotlyChart;
