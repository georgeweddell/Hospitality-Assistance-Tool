import { useEffect, useState } from 'react'
import { Bar, CartesianGrid, Cell, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import Card from './Card'
import Hint from './Hint'
import { getJson } from '../api'
import { percent, pounds, poundsRounded, shortDate } from '../format'
import { rangeQuery } from '../dateRange'

// Money on the Sales page: sales £ by day, category and dish for the chosen
// period (GET /sales/summary). Each day is priced at what was charged that day.

const dayLabel = (iso) => new Date(`${iso}T00:00:00Z`).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', timeZone: 'UTC' })

// Each day with the average of it and the 6 days before (fewer at the start).
function withAverage(days) {
  return days.map((d, i) => {
    const window = days.slice(Math.max(0, i - 6), i + 1)
    return { ...d, average: window.reduce((s, w) => s + w.sales, 0) / window.length }
  })
}

// Friday to Sunday, the busy end of the week, in tomato; other days in mustard.
const weekend = (iso) => [0, 5, 6].includes(new Date(`${iso}T00:00:00Z`).getUTCDay())

function Figure({ label, value, sub, tone }) {
  return (
    <div className={`tile min-h-[132px] ${tone}`}>
      <span className="tile-label">{label}{sub && ` · ${sub}`}</span>
      <span className="figure text-[clamp(2.5rem,4vw,3.75rem)]">{value}</span>
    </div>
  )
}

function Key({ className, label }) {
  return (
    <span className="flex items-center gap-1.5">
      <span className={className} />
      {label}
    </span>
  )
}

function DayTooltip({ active, payload }) {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  const weekday = new Date(`${d.day}T00:00:00Z`).toLocaleDateString('en-GB', { weekday: 'long', timeZone: 'UTC' })
  return (
    <div className="chart-tip">
      <p className="chart-tip-title">{shortDate(d.day)}</p>
      <p className="chart-tip-kicker">{weekday}</p>
      <div className="chart-tip-figures">
        <div><div className="chart-tip-value">{pounds(d.sales)}</div><div className="chart-tip-label">sales</div></div>
        <div><div className="chart-tip-value">{Math.round(d.units)}</div><div className="chart-tip-label">sold</div></div>
        <div><div className="chart-tip-value">{pounds(d.average)}</div><div className="chart-tip-label">7-day average</div></div>
      </div>
    </div>
  )
}

function Sellers({ title, dishes, className }) {
  return (
    <Card title={title} flush className={className}>
      <table className="table">
        <tbody>
          {dishes.map((d) => (
            <tr key={d.dish_id}>
              <td>
                <a href={`#/menu/${d.dish_id}`} className="font-semibold hover:text-accent">{d.name}</a>
                <span className="block text-xs text-muted">{d.category ?? 'No category'}</span>
              </td>
              <td className="num text-right text-muted">{Math.round(d.units)} sold</td>
              <td className="num text-right font-semibold">{poundsRounded(d.sales)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  )
}

function SalesMoney({ range, coverage }) {
  const [summary, setSummary] = useState(null)
  const [error, setError] = useState(null)

  // coverage changes whenever the app reloads its data (e.g. after sales are saved or imported).
  useEffect(() => {
    let ignore = false
    getJson(`/sales/summary?${rangeQuery(range)}`)
      .then((s) => { if (!ignore) { setSummary(s); setError(null) } })
      .catch((err) => { if (!ignore) setError(err.message) })
    return () => { ignore = true }
  }, [range, coverage])

  if (error) return <p className="alert-error">{error}</p>
  if (!summary || summary.total_sales === 0) return null

  const days = withAverage(summary.days)
  const trading = summary.days.filter((d) => d.sales > 0)
  const busiest = trading.reduce((best, d) => (d.sales > best.sales ? d : best), trading[0])
  const shown = Math.min(5, Math.floor(summary.dishes.length / 2))

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Figure label="dish sales" value={poundsRounded(summary.total_sales)} tone="tile-tomato corner-tr" />
        <Figure label="dishes sold" value={Math.round(summary.total_units).toLocaleString('en-GB')} tone="tile-outline" />
        <Figure label="busiest day" value={poundsRounded(busiest.sales)} sub={shortDate(busiest.day).toLowerCase()} tone="tile-mustard" />
        <Figure label="average day" value={poundsRounded(summary.total_sales / trading.length)}
                sub={`${trading.length} trading`} tone="tile-basil corner-tl" />
      </div>

      <Card title="Sales by day"
            aside={
              <span className="flex flex-wrap items-center gap-4 font-mono text-xs text-ink">
                <Key className="h-3 w-3 rounded-[3px] bg-mustard" label="mon–thu" />
                <Key className="h-3 w-3 rounded-[3px] bg-accent" label="fri–sun" />
                <Key className="h-[3px] w-4 bg-ink" label="7-day average" />
                <Hint align="right" label="About these figures"
                      content="Units sold × the menu price charged that day, including VAT. The line is the average of each day and the six before it." />
              </span>
            }>
        <div className="chart">
          <ResponsiveContainer width="100%" height={260}>
            <ComposedChart data={days} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
              <CartesianGrid vertical={false} />
              <XAxis dataKey="day" tickFormatter={dayLabel} minTickGap={24} tickLine={false} />
              <YAxis tickFormatter={(v) => poundsRounded(v)} width={64} tickLine={false} axisLine={false} />
              <Tooltip content={<DayTooltip />} cursor={{ fill: 'var(--line)', fillOpacity: 0.5 }}
                       isAnimationActive={false} offset={16} wrapperStyle={{ outline: 'none' }} />
              <Bar dataKey="sales" radius={[6, 6, 2, 2]}>
                {days.map((d) => <Cell key={d.day} fill={weekend(d.day) ? 'var(--accent)' : 'var(--mustard)'} />)}
              </Bar>
              <Line dataKey="average" stroke="var(--ink)" strokeWidth={3} dot={false} type="monotone" />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </Card>

      <Card title="By category" flush>
        <ul className="divide-y divide-line border-t border-line">
          {summary.categories.map((c) => {
            const share = (c.sales / summary.total_sales) * 100
            return (
              <li key={c.category ?? 'none'} className="grid grid-cols-[8rem_1fr_5rem_4rem] items-center gap-4 px-5 py-3">
                <span className="font-semibold">{c.category ?? 'No category'}</span>
                <div className="progress"><div className="progress-bar" style={{ width: `${share}%` }} /></div>
                <span className="num text-right font-semibold">{poundsRounded(c.sales)}</span>
                <span className="num text-right text-muted">{percent(share, 0)}</span>
              </li>
            )
          })}
        </ul>
      </Card>

      {shown > 0 && (
        <div className="grid gap-5 lg:grid-cols-2">
          <Sellers title="Best sellers" dishes={summary.dishes.slice(0, shown)} className="corner-tl bg-basil-soft" />
          <Sellers title="Lowest sellers" dishes={summary.dishes.slice(-shown).reverse()} className="corner-tr bg-plum-soft" />
        </div>
      )}
    </div>
  )
}

export default SalesMoney
