import Hint from './Hint'
import QuadrantBadge from './QuadrantBadge'
import { QUADRANT_ORDER, quadrantColor, quadrantTextColor } from '../quadrants'
import { percent, poundsRounded } from '../format'
import { isFullMonth, previousLabel } from '../dateRange'
import { IMPACT_EXPLAINED, explain } from '../actionText'

// Totals for a set of analysed dishes.
//   Contribution = sum of (margin x units sold)
//   Sales        = sum of (menu price x units sold)
//   Gross margin = contribution / sales
function summarise(dishes) {
  let contribution = 0
  let sales = 0
  let units = 0
  for (const d of dishes) {
    contribution += d.margin_pounds * d.units_sold
    sales += d.menu_price * d.units_sold
    units += d.units_sold
  }
  return { contribution, sales, units, grossMargin: sales > 0 ? (contribution / sales) * 100 : 0 }
}

const pctChange = (now, before) => (before > 0 ? ((now - before) / before) * 100 : null)

// ▲ / ▼ with the size of the change. Rises in green; falls stay neutral.
function Delta({ value, format = (v) => `${v}%` }) {
  if (value == null) return null
  const rounded = Math.round(value * 10) / 10
  if (rounded === 0) return <span className="chip chip-muted num">=</span>
  const up = rounded > 0
  return (
    <span className={`chip num ${up ? '' : 'chip-muted'}`}
          style={up ? { color: quadrantTextColor('Star'), backgroundColor: `${quadrantColor('Star')}1f` } : undefined}>
      {up ? '▲' : '▼'} {format(Math.abs(rounded))}
    </span>
  )
}

function Figure({ label, value, children }) {
  return (
    <div className="card flex flex-col gap-3 px-5 py-[18px]">
      <p className="label">{label}</p>
      <p className="stat-value">{value}</p>
      <div className="min-h-[22px]">{children}</div>
    </div>
  )
}

const OffChip = ({ children }) => <span className="chip chip-muted">{children}</span>

// What moved between the previous period and this one, as data rows.
function changesSince(dishes, prevDishes, allDishes, range) {
  const prevById = Object.fromEntries(prevDishes.map((d) => [d.dish_id, d]))
  const nowById = Object.fromEntries(dishes.map((d) => [d.dish_id, d]))
  const menuById = Object.fromEntries(allDishes.map((d) => [d.id, d]))
  const rows = []

  for (const d of dishes) {
    const p = prevById[d.dish_id]
    if (!p) {
      rows.push({ id: d.dish_id, name: d.dish_name, rank: 2, from: <OffChip>New</OffChip>, to: d.quadrant, units: null })
    } else if (p.quadrant !== d.quadrant) {
      rows.push({ id: d.dish_id, name: d.dish_name, rank: d.quadrant === 'Star' ? 0 : 1,
        from: <QuadrantBadge quadrant={p.quadrant} />, to: d.quadrant, units: pctChange(d.units_sold, p.units_sold) })
    }
  }
  for (const p of prevDishes) {
    if (nowById[p.dish_id]) continue
    const until = menuById[p.dish_id]?.on_menu_until
    rows.push({ id: p.dish_id, name: p.dish_name, rank: 3, from: <QuadrantBadge quadrant={p.quadrant} />,
      toChip: <OffChip>{until && until < range.from ? 'Off menu' : 'Not analysed'}</OffChip>, units: null })
  }
  return rows.sort((a, b) => a.rank - b.rank)
}

function MoveCard({ action, dish, rank, perMonth }) {
  return (
    <div className="card flex flex-col gap-4 p-[22px]">
      <div className="flex items-center justify-between">
        <Hint content={explain(dish)}><QuadrantBadge quadrant={action.quadrant} /></Hint>
        <span className="label num">#{rank}</span>
      </div>
      <a href={`#/menu/${action.dish_id}`} className="font-display text-2xl font-semibold leading-tight hover:text-accent">
        {action.dish_name}
      </a>
      <p className="mt-auto flex flex-wrap items-baseline gap-x-1.5">
        <span className="stat-value whitespace-nowrap">+{poundsRounded(action.impact_pounds)}</span>
        {perMonth && <span className="whitespace-nowrap text-muted">/ month</span>}
      </p>
    </div>
  )
}

function OverviewPage({ dishes, prevDishes, actions, allDishes, range }) {
  const now = summarise(dishes)
  const hasPrev = prevDishes.length > 0
  const before = hasPrev ? summarise(prevDishes) : null
  const vs = previousLabel(range)

  const dishById = Object.fromEntries(dishes.map((d) => [d.dish_id, d]))
  const top = actions.slice(0, 3)

  const counts = Object.fromEntries(QUADRANT_ORDER.map((q) => [q, 0]))
  for (const d of dishes) counts[d.quadrant] += 1
  const prevCounts = Object.fromEntries(QUADRANT_ORDER.map((q) => [q, prevDishes.filter((d) => d.quadrant === q).length]))

  const changes = hasPrev ? changesSince(dishes, prevDishes, allDishes, range) : []

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Figure label="Contribution" value={poundsRounded(now.contribution)}>
          {hasPrev && <Delta value={pctChange(now.contribution, before.contribution)}
                             format={(v) => `${poundsRounded(Math.abs(now.contribution - before.contribution))} · ${v}%`} />}
        </Figure>
        <Figure label="Sales" value={poundsRounded(now.sales)}>
          {hasPrev && <Delta value={pctChange(now.sales, before.sales)} />}
        </Figure>
        <Figure label="Gross margin" value={percent(now.grossMargin)}>
          {hasPrev && <Delta value={now.grossMargin - before.grossMargin} format={(v) => `${v} pts`} />}
        </Figure>
        <Figure label="Dishes sold" value={now.units.toLocaleString('en-GB')}>
          {hasPrev && <Delta value={pctChange(now.units, before.units)} />}
        </Figure>
      </div>

      <section className="space-y-4">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <h2 className="section-title">Top moves</h2>
            <Hint content={IMPACT_EXPLAINED} label="How impact is worked out" />
          </div>
          {actions.length > 0 && <a href="#/actions" className="link">All {actions.length} actions →</a>}
        </div>
        {top.length === 0 ? (
          <div className="empty">No actions</div>
        ) : (
          <div className="grid gap-4 md:grid-cols-3">
            {top.map((a, i) => (
              <MoveCard key={a.dish_id} action={a} dish={dishById[a.dish_id]} rank={i + 1} perMonth={isFullMonth(range)} />
            ))}
          </div>
        )}
      </section>

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1.25fr)_minmax(0,1fr)]">
        <section className="card">
          <div className="card-header">
            <h2 className="section-title">Since {vs}</h2>
            {hasPrev && <span className="count">{changes.length}</span>}
          </div>
          {!hasPrev ? (
            <p className="card-body text-muted">No earlier data</p>
          ) : changes.length === 0 ? (
            <p className="card-body text-muted">No changes</p>
          ) : (
            <table className="table">
              <tbody>
                {changes.slice(0, 6).map((c) => (
                  <tr key={c.id}>
                    <td>
                      <a href={`#/menu/${c.id}`} className="font-semibold hover:text-accent">{c.name}</a>
                    </td>
                    <td className="whitespace-nowrap">
                      <span className="inline-flex items-center gap-1.5">
                        {c.from}
                        <span className="text-muted" aria-label="to">→</span>
                        {c.toChip ?? <QuadrantBadge quadrant={c.to} />}
                      </span>
                    </td>
                    <td className="w-20 text-right">
                      {c.units != null && <Delta value={c.units} format={(v) => `${Math.round(v)}%`} />}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>

        <section className="card flex flex-col gap-4 px-5 py-[18px]">
          <div className="flex items-baseline justify-between gap-2">
            <h2 className="section-title">Menu health</h2>
            <span className="count">{dishes.length}</span>
          </div>
          <div className="flex h-3 gap-0.5 overflow-hidden rounded-full" role="img"
               aria-label={QUADRANT_ORDER.map((q) => `${counts[q]} ${q}s`).join(', ')}>
            {QUADRANT_ORDER.map((q) =>
              counts[q] > 0 ? <div key={q} style={{ flexGrow: counts[q], backgroundColor: quadrantColor(q) }} /> : null
            )}
          </div>
          <ul className="grid grid-cols-2 gap-x-6 gap-y-2.5">
            {QUADRANT_ORDER.map((q) => {
              const diff = counts[q] - prevCounts[q]
              return (
                <li key={q} className="flex items-center gap-2">
                  <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: quadrantColor(q) }} />
                  <span className="num font-semibold">{counts[q]}</span>
                  <span className="text-muted">{q}s</span>
                  {hasPrev && diff !== 0 && (
                    <span className="num text-xs font-semibold text-muted">{diff > 0 ? `▲${diff}` : `▼${-diff}`}</span>
                  )}
                </li>
              )
            })}
          </ul>
        </section>
      </div>
    </div>
  )
}

export default OverviewPage
