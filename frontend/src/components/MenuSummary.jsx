import { QUADRANT_ORDER, quadrantColor } from '../quadrants'
import { percent, poundsRounded } from '../format'

function Stat({ label, value, detail }) {
  return (
    <div className="rounded-xl border border-line bg-surface p-4 shadow-sm">
      <p className="text-sm text-muted">{label}</p>
      <p className="mt-1 text-2xl font-semibold tabular-nums">{value}</p>
      {detail && <p className="mt-0.5 text-xs text-muted">{detail}</p>}
    </div>
  )
}

// Headline figures and the quadrant mix, worked out from data the API
// already returns. Totals cover analysed dishes only.
function MenuSummary({ dishes, actions, excludedCount }) {
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
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Stat label="Contribution" value={poundsRounded(contribution)} detail="Margin × units sold" />
        <Stat label="Gross margin" value={percent(grossMargin)} detail={`On ${poundsRounded(revenue)} sales`} />
        <Stat label="Opportunity identified" value={poundsRounded(opportunity)} detail={`Across ${actions.length} actions`} />
        <Stat
          label="Dishes analysed"
          value={dishes.length}
          detail={excludedCount > 0 ? `${excludedCount} awaiting data` : 'All dishes complete'}
        />
      </div>

      <div className="rounded-xl border border-line bg-surface p-4 shadow-sm">
        <div className="flex items-baseline justify-between">
          <p className="text-sm font-medium">Menu health</p>
          <p className="text-sm text-muted">{dishes.length} dishes</p>
        </div>
        <div className="mt-3 flex h-2.5 overflow-hidden rounded-full bg-bg">
          {QUADRANT_ORDER.map((q) =>
            counts[q] > 0 ? (
              <div key={q} style={{ width: `${(counts[q] / dishes.length) * 100}%`, backgroundColor: quadrantColor(q) }} />
            ) : null
          )}
        </div>
        <ul className="mt-3 flex flex-wrap gap-x-6 gap-y-1 text-sm">
          {QUADRANT_ORDER.map((q) => (
            <li key={q} className="flex items-center gap-2">
              <span className="h-2 w-2 rounded-full" style={{ backgroundColor: quadrantColor(q) }} />
              <span className="font-medium tabular-nums">{counts[q]}</span>
              <span className="text-muted">{q}{counts[q] === 1 ? '' : 's'}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}

export default MenuSummary
