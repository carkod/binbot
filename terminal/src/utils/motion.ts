import type { Variants } from "motion/react";

export const chartTransition = { duration: 0.3, ease: "easeOut" } as const;

// Plotly uses milliseconds and its own easing names.
export const liveChartTransition = {
  duration: chartTransition.duration * 1000,
  easing: "cubic-out",
  ordering: "axes first",
} as const;

// Animate opacity and position without changing chart dimensions.
export const chartRevealVariants: Variants = {
  hidden: { opacity: 0, y: 12 },
  visible: { opacity: 1, y: 0 },
};
