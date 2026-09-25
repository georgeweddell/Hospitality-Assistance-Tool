import { percentMove, priceMove } from '../priceChanges'
import { pounds, poundsRounded, shortDate } from '../format'

// The biggest ingredient price rises (alerts), for the Overview.
export function PriceRiseList({ changes, limit = 4 }) {
  const rises = changes.filter((c) => c.is_alert).slice(0, limit)
  if (rises.length === 0) return <p className="card-body font-mono text-sm text-muted">none</p>
  return (
    <ul>
      {rises.map((c) => {
        const perPlate = c.dishes.map((d) => d.per_plate)
        const low = Math.min(...perPlate)
        const high = Math.max(...perPlate)
        return (
          <li key={`${c.ingredient_id}-${c.day}`}
              className="grid grid-cols-[minmax(0,1fr)_auto] items-baseline gap-x-4 gap-y-1 border-t-[1.5px] border-dashed border-line-strong px-5 py-3">
            <a href="#/ingredients" className="font-bold hover:underline">{c.name}</a>
            <span className="figure text-[1.5rem] text-accent">{c.period_effect < 0 ? '−' : '+'}{poundsRounded(Math.abs(c.period_effect))}</span>
            <span className="num text-sm">
              {priceMove(c)} <span className="chip chip-accent ml-1">{percentMove(c)}</span>
            </span>
            <span className="num text-right text-xs text-muted">
              {shortDate(c.day).toLowerCase()}{c.after_period && ' · after the period'}
            </span>
            <span className="col-span-2 font-mono text-xs text-muted">
              {c.dishes.length} dish{c.dishes.length === 1 ? '' : 'es'} · +{low === high ? pounds(low) : `${pounds(low)}–${pounds(high)}`} a plate
            </span>
          </li>
        )
      })}
    </ul>
  )
}
