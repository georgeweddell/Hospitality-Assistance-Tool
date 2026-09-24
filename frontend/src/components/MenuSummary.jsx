import { QUADRANT_ORDER, quadrantColor } from '../quadrants'
import { percent, poundsRounded } from '../format'

function Stat({ label, value }) {
  return (
    <div className="card flex flex-col gap-2.5 px-5 py-[18px]">
      <p className="label">{label}</p>
      <p className="stat-value">{value}</p>
    </div>
  )
}

// Headline figures and the quadrant mix, worked out from data the API
// already returns. Totals cover analysed dishes only.
//   Contribution = sum of (margin x units sold)
//   Gross margin = contribution / sales (sum of menu price x units sold)
function MenuSummary({ dishes, actions }) {
  let contribution = 0
  let revenue = 0
  for (const d of dishes) {
    contribution += d.margin_pounds * d.units_sold
    revenue += d.menu_price * d.units_sold
  }
  const grossMargin = revenue > 0 ? (contribution / revenue) * 100 : 0
  const opportunity = actions.reduce((sum, a) => sum + a.impact_pounds, 0)

  const counts = Object.fromEntries(QUADRANT_ORDER.map((q) => [q, 0]))
  for (const d of dishes) counts[d.quadrant] += 1

  return (
    <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
      <Stat label="Contribution" value={poundsRounded(contribution)} />
      <Stat label="Gross margin" value={percent(grossMargin)} />
      <Stat label="Opportunity" value={poundsRounded(opportunity)} />

      <div className="card flex flex-col gap-3 px-5 py-[18px]">
        <p className="label">Menu health · {dishes.length} dishes</p>
        <div className="flex h-2.5 gap-0.5 overflow-hidden rounded-full" role="img"
             aria-label={QUADRANT_ORDER.map((q) => `${counts[q]} ${q}s`).join(', ')}>
          {QUADRANT_ORDER.map((q) =>
            counts[q] > 0 ? <div key={q} style={{ flexGrow: counts[q], backgroundColor: quadrantColor(q) }} /> : null
          )}
        </div>
        <ul className="flex justify-between text-sm">
          {QUADRANT_ORDER.map((q) => (
            <li key={q} className="flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full" style={{ backgroundColor: quadrantColor(q) }} />
              <span className="num font-semibold">{counts[q]}</span>
              <span className="sr-only">{q}s</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}

export default MenuSummary
