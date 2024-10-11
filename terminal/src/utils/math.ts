const checkValue = value => {
  if (value === "" || value === null || value === undefined) {
    return true
  }
  return false
}

const checkMinValue = value => {
  /**
   * Check float value reaches minimum
   */
  const a = parseFloat(value)
  // Min required to operate
  const b = parseFloat("0.001")
  if (a > b) {
    return true
  }
  return false
}

const checkBalance = value => {
  if (value === "0" || value === 0 || value === undefined || value === null) {
    return true
  }
  return false
}

const getCurrentPairBalance = (balances, currentAsset) => {
  let qty = "0"
  balances.forEach(x => {
    if (currentAsset === x.asset) {
      qty = x.free
    }
  })
  return qty
}

const toPercentage = value => {
  if (checkValue(value)) {
    return null
  }
  const decimal = parseFloat(value) * 100
  return decimal
}

const percentageToFloat = value => {
  if (checkValue(value)) {
    return null
  }
  const tofloat = parseFloat(value) / 100
  return tofloat
}

const replaceZeros = value => {
  return value.replace(/^0+/, "")
}

const roundDecimals = (num, decimals = 2) => {
  const number =
    Math.round((num + Number.EPSILON) * Math.pow(10, decimals)) /
    Math.pow(10, decimals)
  return number
}

export {
  checkValue,
  checkMinValue,
  checkBalance,
  getCurrentPairBalance,
  toPercentage,
  percentageToFloat,
  replaceZeros,
  roundDecimals,
}