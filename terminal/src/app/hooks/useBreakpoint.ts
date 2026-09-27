import { useCallback, useEffect, useState } from "react";

export type Breakpoint = "xs" | "sm" | "md" | "lg" | "xl" | "xxl";

const resolveBreakpoint = (width: number): Breakpoint => {
  if (width < 576) return "xs";
  if (width < 768) return "sm";
  if (width < 992) return "md";
  if (width < 1200) return "lg";
  if (width < 1440) return "xl";
  return "xxl";
};

export const useBreakpoint = () => {
  const [size, setSize] = useState(() => resolveBreakpoint(window.innerWidth));
  const update = useCallback(
    () => setSize(resolveBreakpoint(window.innerWidth)),
    [setSize],
  );

  useEffect(() => {
    window.addEventListener("resize", update);
    return () => window.removeEventListener("resize", update);
  }, [update]);

  return size;
};
