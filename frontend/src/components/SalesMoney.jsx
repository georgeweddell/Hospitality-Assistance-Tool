import { useEffect, useState } from 'react'
import { Bar, CartesianGrid, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
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

function Figure({ label, value, sub }) {
  return (
    <div className="card flex flex-col gap-2.5 px-5 py-[18px]">
      <p className="label">{label}</p>
      <p className="stat-value text-[1.625rem]">{value}</p>
      {sub && <p className="num text-sm text-muted">{sub}</p>}
    </div>
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

function Sellers({ title, dishes }) {
  return (
    <Card title={title} flush>
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
        <Figure label="Dish sales" value={poundsRounded(summary.total_sales)} />
        <Figure label="Dishes sold" value={Math.round(summary.total_units).toLocaleString('en-GB')} />
        <Figure label="Busiest day" value={poundsRounded(busiest.sales)} sub={shortDate(busiest.day)} />
        <Figure label="Average day" value={poundsRounded(summary.total_sales / trading.length)}
                sub={`${trading.length} trading days`} />
      </div>

      <Card title="Sales by day"
            aside={<Hint align="right" label="About these figures"
                         content="Units sold × the menu price charged that day, including VAT. The line is the average of each day and the six before it." />}>
        <div className="chart">
          <ResponsiveContainer width="100%" height={260}>
            <ComposedChart data={days} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
              <CartesianGrid vertical={false} />
              <XAxis dataKey="day" tickFormatter={dayLabel} minTickGap={24} tickLine={false} />
              <YAxis tickFormatter={(v) => poundsRounded(v)} width={64} tickLine={false} axisLine={false} />
              <Tooltip content={<DayTooltip />} cursor={{ fill: 'var(--line)', fillOpacity: 0.5 }}
                       isAnimationActive={false} offset={16} wrapperStyle={{ outline: 'none' }} />
              <Bar dataKey="sales" fill="var(--accent)" fillOpacity={0.85} radius={[3, 3, 0, 0]} />
              <Line dataKey="average" stroke="var(--ink)" strokeWidth={2} dot={false} type="monotone" />
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
          <Sellers title="Best sellers" dishes={summary.dishes.slice(0, shown)} />
          <Sellers title="Lowest sellers" dishes={summary.dishes.slice(-shown).reverse()} />
        </div>
      )}
    </div>
  )
}

export default SalesMoney
