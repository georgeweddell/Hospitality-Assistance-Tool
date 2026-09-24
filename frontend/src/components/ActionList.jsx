import { useState } from 'react'
import Card from './Card'
import QuadrantBadge from './QuadrantBadge'
import { QUADRANTS, quadrantColor } from '../quadrants'
import { percent, pounds, poundsRounded } from '../format'

const ACTION_QUADRANTS = ['Plowhorse', 'Puzzle', 'Dog']

// The number that put the dish in its quadrant, next to the line it missed.
function reason(dish) {
  if (!dish) return ''
  if (dish.quadrant === 'Puzzle') {
    return `${percent(dish.menu_mix_percent)} of sales vs ${percent(dish.popularity_threshold)} needed`
  }
  return `${pounds(dish.margin_pounds)} margin vs ${pounds(dish.profitability_threshold)} average`
}

function OpportunityCard({ quadrant, total, count, active, onClick }) {
  const color = quadrantColor(quadrant)
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={`rounded-xl border bg-surface p-4 text-left shadow-sm transition-colors ${
        active ? 'border-accent ring-1 ring-accent' : 'border-line hover:border-muted'
      }`}
    >
      <div className="flex items-center gap-2 text-sm">
        <span className="h-2 w-2 rounded-full" style={{ backgroundColor: color }} />
        <span className="font-medium">{QUADRANTS[quadrant].action}</span>
      </div>
      <p className="mt-2 text-xl font-semibold tabular-nums">{poundsRounded(total)}</p>
      <p className="text-xs text-muted">
        {count} {quadrant}{count === 1 ? '' : 's'}
      </p>
    </button>
  )
}

function ActionList({ actions, dishes }) {
  const [filter, setFilter] = useState(null)

  const dishById = Object.fromEntries(dishes.map((d) => [d.dish_id, d]))
  const shown = filter ? actions.filter((a) => a.quadrant === filter) : actions
  const maxImpact = Math.max(...actions.map((a) => a.impact_pounds), 1)

  const byQuadrant = ACTION_QUADRANTS.map((q) => {
    const items = actions.filter((a) => a.quadrant === q)
    return { quadrant: q, count: items.length, total: items.reduce((s, a) => s + a.impact_pounds, 0) }
  })

  return (
    <div className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-3">
        {byQuadrant.map((g) => (
          <OpportunityCard
            key={g.quadrant}
            {...g}
            active={filter === g.quadrant}
            onClick={() => setFilter(filter === g.quadrant ? null : g.quadrant)}
          />
        ))}
      </div>

      <Card
        title={filter ? `${QUADRANTS[filter].action} actions` : 'Priority actions'}
        aside={filter && (
          <button type="button" onClick={() => setFilter(null)} className="font-medium text-accent hover:underline">
            Show all
          </button>
        )}
        flush
      >
        {shown.length === 0 ? (
          <p className="px-5 pb-5 text-sm text-muted">No actions. Every analysed dish is a Star.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-line text-left text-xs uppercase tracking-wide text-muted">
                  <th className="w-10 py-2 pl-5 font-medium">#</th>
                  <th className="px-3 py-2 font-medium">Dish</th>
                  <th className="px-3 py-2 font-medium">Action</th>
                  <th className="hidden px-3 py-2 font-medium md:table-cell">Why</th>
                  <th className="py-2 pl-3 pr-5 text-right font-medium">Impact</th>
                </tr>
              </thead>
              <tbody>
                {shown.map((item, i) => {
                  const dish = dishById[item.dish_id]
                  return (
                    <tr key={item.dish_id} className="border-b border-line last:border-0">
                      <td className="py-3 pl-5 tabular-nums text-muted">{i + 1}</td>
                      <td className="px-3 py-3">
                        <div className="font-medium">{item.dish_name}</div>
                        <div className="text-xs text-muted">{dish?.category}</div>
                      </td>
                      <td className="px-3 py-3">
                        <div className="mb-1"><QuadrantBadge quadrant={item.quadrant} /></div>
                        <div className="text-muted">{item.action}</div>
                      </td>
                      <td className="hidden px-3 py-3 text-muted md:table-cell">{reason(dish)}</td>
                      <td className="py-3 pl-3 pr-5 text-right">
                        <div className="font-semibold tabular-nums">{pounds(item.impact_pounds)}</div>
                        <div className="ml-auto mt-1.5 h-1 w-24 overflow-hidden rounded-full bg-bg">
                          <div
                            className="ml-auto h-full rounded-full"
                            style={{
                              width: `${(item.impact_pounds / maxImpact) * 100}%`,
                              backgroundColor: quadrantColor(item.quadrant),
                            }}
                          />
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  )
}

export default ActionList
