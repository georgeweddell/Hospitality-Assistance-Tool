import { useState } from 'react'
import Hint from './Hint'
import QuadrantBadge from './QuadrantBadge'
import { quadrantColor } from '../quadrants'
import { percent, pounds, poundsRounded } from '../format'
import { IMPACT_EXPLAINED, VERB, explain } from '../actionText'

const FILTERS = ['Plowhorse', 'Puzzle', 'Dog']

function ActionList({ actions, dishes }) {
  const [filter, setFilter] = useState(null)

  const dishById = Object.fromEntries(dishes.map((d) => [d.dish_id, d]))
  const shown = filter ? actions.filter((a) => a.quadrant === filter) : actions
  const maxImpact = Math.max(...actions.map((a) => a.impact_pounds), 1)
  const total = (q) => actions.filter((a) => a.quadrant === q).reduce((s, a) => s + a.impact_pounds, 0)

  return (
    <section className="card">
      <div className="card-header flex-wrap items-center">
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
        <p className="card-body text-muted">No actions</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="table min-w-[640px]">
            <thead>
              <tr>
                <th className="w-10">#</th>
                <th>Dish</th>
                <th className="w-36">Quadrant</th>
                <th className="w-24 text-right">Margin</th>
                <th className="w-32 text-right">Share of sales</th>
                <th className="w-36 text-right">
                  <span className="inline-flex items-center gap-1.5">
                    Impact <Hint content={IMPACT_EXPLAINED} label="How impact is worked out" align="right" />
                  </span>
                </th>
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
                    </td>
                    <td><Hint content={explain(dish)}><QuadrantBadge quadrant={item.quadrant} /></Hint></td>
                    <td className="num text-right">{dish ? pounds(dish.margin_pounds) : '—'}</td>
                    <td className="num text-right">{dish ? percent(dish.menu_mix_percent) : '—'}</td>
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
