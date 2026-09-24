// £12.50, £1,089.01
export function pounds(value) {
  return `£${value.toLocaleString('en-GB', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

// £1,234 (whole pounds, for headline totals)
export function poundsRounded(value) {
  return `£${Math.round(value).toLocaleString('en-GB')}`
}

// 12.5%
export function percent(value, decimals = 1) {
  return `${value.toFixed(decimals)}%`
}

// Short label for a base unit: g / ml / each
export function unitLabel(unit) {
  return { gram: 'g', ml: 'ml', each: 'each' }[unit] ?? unit
}

// Prices are stored per base unit (per g / ml / each). Show them the way a
// kitchen reads them: £8.20/kg, £9.00/l, £0.30 each.
export function priceForDisplay(pricePerUnit, unit) {
  if (unit === 'gram') return `£${(pricePerUnit * 1000).toFixed(2)}/kg`
  if (unit === 'ml') return `£${(pricePerUnit * 1000).toFixed(2)}/l`
  return `£${pricePerUnit.toFixed(2)} each`
}

// invoice -> Invoice, supplier_list -> Supplier list
export function sourceLabel(source) {
  return { invoice: 'Invoice', supplier_list: 'Supplier list', manual: 'Manual', benchmark: 'Benchmark' }[source] ?? source
}

// 2026-09-12 -> 12 Sep 2026
export function shortDate(isoDate) {
  return new Date(isoDate).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
}
