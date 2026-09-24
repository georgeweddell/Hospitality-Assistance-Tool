import { useEffect, useState } from 'react'
import Card from './Card'
import { getJson, putJson } from '../api'
import { eachDay, rangeLabel, rangeQuery } from '../dateRange'
import { CATEGORIES } from '../categories'

const INPUT = 'w-28 rounded-lg border border-line bg-surface px-2.5 py-1.5 text-right tabular-nums text-ink focus:border-accent focus:outline-none disabled:opacity-50'

// One square per day in the range, filled where sales are recorded, grouped by month.
function CoverageStrip({ range, coverage }) {
  const covered = new Set(coverage.days_with_sales)
  const days = eachDay(range.from, range.to)
  const months = []
  for (const d of days) {
    const key = d.slice(0, 7)
    if (!months.length || months[months.length - 1].key !== key) months.push({ key, days: [] })
    months[months.length - 1].days.push(d)
  }
  const monthLabel = (key) =>
    new Date(`${key}-01T00:00:00Z`).toLocaleDateString('en-GB', { month: 'short', year: 'numeric', timeZone: 'UTC' })

  return (
    <div className="space-y-2">
      {months.map((m) => (
        <div key={m.key} className="flex items-center gap-3">
          <span className="w-20 shrink-0 text-xs text-muted">{monthLabel(m.key)}</span>
          <div className="flex flex-wrap gap-1">
            {m.days.map((d) => (
              <span
                key={d}
                aria-label={`${d}: ${covered.has(d) ? 'sales recorded' : 'no sales'}`}
                className={`h-3.5 w-3.5 rounded-sm ${covered.has(d) ? 'bg-accent' : 'bg-line'}`}
              />
            ))}
          </div>
        </div>
      ))}
      <p className="text-xs text-muted">
        <span className="mr-1 inline-block h-2.5 w-2.5 rounded-sm bg-accent align-middle" /> sales recorded
        <span className="ml-4 mr-1 inline-block h-2.5 w-2.5 rounded-sm bg-line align-middle" /> nothing recorded
      </p>
    </div>
  )
}

// Enter a total per dish for exactly this period (for owners without till data).
function ManualEntry({ range, onSaved }) {
  const [entries, setEntries] = useState(null)
  const [values, setValues] = useState({})
  const [error, setError] = useState(null)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    let ignore = false
    getJson(`/sales/entries?${rangeQuery(range)}`)
      .then((rows) => {
        if (ignore) return
        setEntries(rows)
        setValues(Object.fromEntries(rows.map((r) => [r.dish_id, r.units_sold != null ? String(r.units_sold) : ''])))
        setError(null)
        setSaved(false)
      })
      .catch((err) => { if (!ignore) setError(err.message) })
    return () => { ignore = true }
  }, [range])

  if (error && !entries) return <p className="text-sm text-danger">{error}</p>
  if (!entries) return <p className="text-sm text-muted">Loading…</p>
  if (entries.length === 0) return <p className="text-sm text-muted">No dishes were on the menu in this period.</p>

  const editable = entries.filter((e) => e.other_records === 0)
  const invalid = editable.some((e) => values[e.dish_id] !== '' && !(Number.isInteger(Number(values[e.dish_id])) && Number(values[e.dish_id]) >= 0))

  const save = () => {
    if (invalid) return setError('Units sold must be whole numbers, 0 or more.')
    setSaving(true)
    setError(null)
    putJson(`/sales/entries?${rangeQuery(range)}`, editable.map((e) => ({
      dish_id: e.dish_id,
      units_sold: values[e.dish_id] === '' ? null : Number(values[e.dish_id]),
    })))
      .then((rows) => {
        setEntries(rows)
        setSaved(true)
        onSaved()
      })
      .catch((err) => setError(err.message))
      .finally(() => setSaving(false))
  }

  const groups = [...CATEGORIES, null]
    .map((c) => ({ c, rows: entries.filter((e) => (e.category ?? null) === c) }))
    .filter((g) => g.rows.length > 0)

  return (
    <div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[480px] text-sm">
          <tbody>
            {groups.map(({ c, rows }) => [
              <tr key={`h-${c}`}>
                <th colSpan={2} className="pb-1 pl-5 pt-4 text-left text-xs font-medium uppercase tracking-wide text-muted">
                  {c ?? 'No category'}
                </th>
              </tr>,
              ...rows.map((e) => (
                <tr key={e.dish_id} className="border-b border-line last:border-0">
                  <td className="py-2 pl-5 pr-3">
                    <div className="font-medium">{e.dish_name}</div>
                    {e.other_records > 0 && (
                      <div className="text-xs text-muted">Already has daily sales in this period</div>
                    )}
                  </td>
                  <td className="py-2 pl-3 pr-5 text-right">
                    <input
                      type="number" min="0" step="1" inputMode="numeric"
                      value={e.other_records > 0 ? '' : values[e.dish_id]}
                      placeholder={e.other_records > 0 ? '—' : 'units'}
                      disabled={e.other_records > 0}
                      onChange={(ev) => { setValues({ ...values, [e.dish_id]: ev.target.value }); setSaved(false) }}
                      className={INPUT}
                      aria-label={`Units sold: ${e.dish_name}`}
                    />
                  </td>
                </tr>
              )),
            ])}
          </tbody>
        </table>
      </div>
      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-line px-5 py-3">
        <p className="text-xs text-muted">
          Every dish on the menu in this period is analysed, so a blank counts as 0 sold.
          If a dish wasn't on the menu, change its menu dates on its dish page.
        </p>
        <div className="flex items-center gap-3">
          {saved && <span className="text-sm text-muted">Saved</span>}
          {error && <span className="text-sm text-danger">{error}</span>}
          <button type="button" onClick={save} disabled={saving || editable.length === 0}
                  className="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-accent-ink hover:opacity-90 disabled:opacity-50">
            {saving ? 'Saving…' : 'Save sales'}
          </button>
        </div>
      </div>
    </div>
  )
}

function SalesPage({ range, coverage, onSaved }) {
  const covered = coverage.days_with_sales.length
  return (
    <div className="space-y-6">
      <Card title="Sales data in this period" aside={`${covered} day${covered === 1 ? '' : 's'} with sales`}>
        <CoverageStrip range={range} coverage={coverage} />
      </Card>

      <Card title={`Enter totals for ${rangeLabel(range)}`} flush>
        <p className="px-5 text-sm text-muted">
          If you don't have till data, enter how many of each dish you sold in this period.
          Dishes with daily sales here are already counted and can't take a total as well.
        </p>
        <ManualEntry range={range} onSaved={onSaved} />
      </Card>
    </div>
  )
}

export default SalesPage
