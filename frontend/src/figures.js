// Totals for a set of analysed dishes (classifications), shared by the Overview
// and Insights pages.
//   Contribution = sum of (margin x units sold)
//   Sales        = sum of (menu price x units sold)
//   Gross margin = contribution / sales
//   Avg margin   = contribution / units (the sales-weighted average margin per dish sold)
export function summarise(dishes) {
  let contribution = 0
  let sales = 0
  let units = 0
  for (const d of dishes) {
    contribution += d.margin_pounds * d.units_sold
    sales += d.menu_price * d.units_sold
    units += d.units_sold
  }
  return {
    contribution, sales, units,
    grossMargin: sales > 0 ? (contribution / sales) * 100 : 0,
    avgMargin: units > 0 ? contribution / units : 0,
  }
}

export const pctChange = (now, before) => (before > 0 ? ((now - before) / before) * 100 : null)
