// £12.50
export function pounds(value) {
  return `£${value.toFixed(2)}`
}

// £1,234 (whole pounds, for headline totals)
export function poundsRounded(value) {
  return `£${Math.round(value).toLocaleString('en-GB')}`
}

// 12.5%
export function percent(value, decimals = 1) {
  return `${value.toFixed(decimals)}%`
}
