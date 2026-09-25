import { useState } from 'react'
import Hint from './Hint'
import QuadrantBadge from './QuadrantBadge'
import TicketRail from './TicketRail'
import { percent, pounds, poundsRounded } from '../format'
import { IMPACT_EXPLAINED, VERB, explain, proposal } from '../actionText'

const FILTERS = ['Plowhorse', 'Puzzle', 'Dog']
const ON_RAIL = 5

// The full ranked action list: the top five hang on the ticket rail, the rest
// follow in a table with the same ranking.
function ActionList({ actions, dishes }) {
  const [filter, setFilter] = useState(null)

  const dishById = Object.fromEntries(dishes.map((d) => [d.dish_id, d]))
  const shown = filter ? actions.filter((a) => a.quadrant === filter) : actions
  const rest = shown.slice(ON_RAIL)
  const maxImpact = Math.max(...rest.map((a) => a.impact_pounds), 1)
  const total = (list) => list.reduce((s, a) => s + a.impact_pounds, 0)

  return (
    <div className="space-y-7">
      <div className="flex flex-wrap items-center gap-3">
        <div className="segmented" role="group" aria-label="Filter actions">
          <button type="button" aria-pressed={filter === null} onClick={() => setFilter(null)}>
            all <span className="num">{actions.length}</span>
          </button>
          {FILTERS.map((q) => (
            <button key={q} type="button" aria-pressed={filter === q} onClick={() => setFilter(filter === q ? null : q)}>
              {VERB[q].toLowerCase()} <span className="num">{actions.filter((a) => a.quadrant === q).length}</span>
            </button>
          ))}
        </div>
        {shown.length > 0 && (
          <span className="chip num border-[1.5px] border-ink bg-mustard px-3 py-1.5 text-[0.8125rem] text-ink">
            +{poundsRounded(total(shown))} total
          </span>
        )}
        <Hint content={IMPACT_EXPLAINED} label="How impact is worked out" />
      </div>

      {shown.length === 0 ? (
        <div className="empty">No changes</div>
      ) : (
        <TicketRail actions={shown.slice(0, ON_RAIL)} categoryOf={(id) => dishById[id]?.category} />
      )}

      {rest.length > 0 && (
        <section className="card">
          <div className="card-header">
            <h2 className="section-title">more changes</h2>
            <span className="count">{rest.length}</span>
          </div>
          <div className="overflow-x-auto">
            <table className="table min-w-[820px]">
              <thead>
                <tr>
                  <th className="w-10">#</th>
                  <th>Dish</th>
                  <th className="w-36">Quadrant</th>
                  <th className="w-24 text-right">Margin</th>
                  <th className="w-32 text-right">Share of sales</th>
                  <th className="w-48">Change</th>
                  <th className="w-44 text-right">Impact</th>
                </tr>
              </thead>
              <tbody>
                {rest.map((item, i) => {
                  const dish = dishById[item.dish_id]
                  return (
                    <tr key={item.dish_id}>
                      <td className="num text-muted">{String(ON_RAIL + i + 1).padStart(2, '0')}</td>
                      <td>
                        <a href={`#/menu/${item.dish_id}`} className="text-lg font-bold hover:text-accent">{item.dish_name}</a>
                      </td>
                      <td><Hint content={explain(dish)}><QuadrantBadge quadrant={item.quadrant} /></Hint></td>
                      <td className="num text-right">{dish ? pounds(dish.margin_pounds) : '—'}</td>
                      <td className="num text-right">{dish ? percent(dish.menu_mix_percent) : '—'}</td>
                      <td>
                        {proposal(item) ? (
                          <Hint content={proposal(item).hint}>
                            <span className="chip num bg-ink text-bg">{proposal(item).text}</span>
                          </Hint>
                        ) : '—'}
                      </td>
                      <td className="text-right">
                        <div className="figure text-[1.75rem] text-accent">+{poundsRounded(item.impact_pounds)}</div>
                        <div className="progress ml-auto mt-1.5 w-28">
                          <div className="progress-bar ml-auto" style={{ width: `${(item.impact_pounds / maxImpact) * 100}%` }} />
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  )
}

export default ActionList
