import type { ComponentType } from "react";
import PlotlyModule from "react-plotly.js";

const resolvePlotlyComponent = (
  moduleValue: unknown,
): ComponentType<Record<string, unknown>> => {
  let component = moduleValue;

  // Vite 8/Rolldown can wrap react-plotly's CommonJS default export.
  for (let index = 0; index < 3; index += 1) {
    if (
      !component ||
      typeof component !== "object" ||
      !("default" in component)
    ) {
      break;
    }

    component = (component as { default: unknown }).default;
  }

  return component as ComponentType<Record<string, unknown>>;
};

const PlotlyChart = resolvePlotlyComponent(PlotlyModule);

export default PlotlyChart;
