import { useState } from 'react'
import QuadrantBadge from './QuadrantBadge'
import { quadrantColor } from '../quadrants'
import { percent, pounds, poundsRounded } from '../format'

// The short verb for each action, shown after the dish name.
const VERB = { Plowhorse: 'Reprice', Puzzle: 'Promote', Dog: 'Review' }
const FILTERS = ['Plowhorse', 'Puzzle', 'Dog']

// The number that put the dish in its quadrant, next to the line it missed.
function reason(dish) {
  if (!dish) return ''
  if (dish.quadrant === 'Puzzle') {
    return `${percent(dish.menu_mix_percent)} of sales · needs ${percent(dish.popularity_threshold)}`
  }
  return `${pounds(dish.margin_pounds)} margin · avg ${pounds(dish.profitability_threshold)}`
}

function ActionList({ actions, dishes }) {
  const [filter, setFilter] = useState(null)

  const dishById = Object.fromEntries(dishes.map((d) => [d.dish_id, d]))
  const shown = filter ? actions.filter((a) => a.quadrant === filter) : actions
  const maxImpact = Math.max(...actions.map((a) => a.impact_pounds), 1)
  const total = (q) => actions.filter((a) => a.quadrant === q).reduce((s, a) => s + a.impact_pounds, 0)

  return (
    <section className="card overflow-hidden">
      <div className="card-header flex-wrap items-center">
        <h2 className="section-title">Priority actions</h2>
        <div className="segmented" role="group" aria-label="Filter actions">
          <button type="button" aria-pressed={filter === null} onClick={() => setFilter(null)}>
            All <span className="num">{actions.length}</span>
          </button>
          {FILTERS.map((q) => (
            <button key={q} type="button" aria-pressed={filter === q} onClick={() => setFilter(filter === q ? null : q)}>
              {VERB[q]} <span className="num font-semibold">{poundsRounded(total(q))}</span>
            </button>
          ))}
        </div>
      </div>

      {shown.length === 0 ? (
        <p className="card-body text-muted">Nothing to act on. Every analysed dish is a Star.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="table min-w-[640px]">
            <thead>
              <tr>
                <th className="w-10">#</th>
                <th>Dish</th>
                <th className="w-32">Quadrant</th>
                <th className="hidden md:table-cell">Why</th>
                <th className="w-36 text-right">Impact</th>
              </tr>
            </thead>
            <tbody>
              {shown.map((item, i) => {
                const dish = dishById[item.dish_id]
                return (
                  <tr key={item.dish_id}>
                    <td className="num text-muted">{i + 1}</td>
                    <td>
                      <a href={`#/menu/${item.dish_id}`} className="font-semibold hover:text-accent">{item.dish_name}</a>
                      <span className="text-muted"> · {VERB[item.quadrant]}</span>
                    </td>
                    <td><QuadrantBadge quadrant={item.quadrant} /></td>
                    <td className="num hidden whitespace-nowrap text-sm text-muted md:table-cell">{reason(dish)}</td>
                    <td className="text-right">
                      <div className="num font-display text-base font-semibold">{pounds(item.impact_pounds)}</div>
                      <div className="ml-auto mt-1.5 h-1 w-24 overflow-hidden rounded-full bg-line">
                        <div className="ml-auto h-full rounded-full"
                             style={{ width: `${(item.impact_pounds / maxImpact) * 100}%`, backgroundColor: quadrantColor(item.quadrant) }} />
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}

export default ActionList
