const checkValue = (value: unknown): boolean => {
  return value === "" || value === null || value === undefined;
};

const toPercentage = (value, decimals: number = 2) => {
  if (checkValue(value)) {
    return null;
  }

  return roundDecimals(parseFloat(value) * 100, decimals);
};

const percentageToFloat = (value) => {
  if (checkValue(value)) {
    return null;
  }

  const tofloat = parseFloat(value) / 100;

  return tofloat;
};

const roundDecimals = (num: number, decimals: number = 2): number => {
  // Use Number.EPSILON to avoid floating point issues
  if (num < 0) return -roundDecimals(-num, decimals);

  const factor = Math.pow(10, decimals);

  const rounding = Math.round((num + Number.EPSILON) * factor) / factor;

  return parseFloat(rounding.toFixed(decimals));
};

const floatSafe = (value: unknown): number => {
  return typeof value === "string" || typeof value === "number"
    ? parseFloat(String(value))
    : 0;
};

const isPositiveFinite = (value: number): boolean => {
  return Number.isFinite(value) && value > 0;
};

// Round down to the nearest multiple, e.g. timestamps to interval boundaries.
const floorToMultiple = (value: number, interval: number): number => {
  return Math.floor(value / interval) * interval;
};

export {
  checkValue,
  toPercentage,
  percentageToFloat,
  roundDecimals,
  floatSafe,
  isPositiveFinite,
  floorToMultiple,
};
