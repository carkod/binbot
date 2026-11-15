import type { Variants } from "motion/react";

// Animate opacity and position without changing chart dimensions.
export const chartRevealVariants: Variants = {
  hidden: { opacity: 0, y: 12 },
  visible: { opacity: 1, y: 0 },
};
