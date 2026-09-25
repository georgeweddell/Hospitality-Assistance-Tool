import { useEffect, useState } from 'react'
import Card from './Card'
import Hint from './Hint'
import SalesMoney from './SalesMoney'
import usePageImport from '../usePageImport'
import { getJson, putJson } from '../api'
import { daysBetween, eachDay, rangeLabel, rangeQuery } from '../dateRange'
import { CATEGORIES } from '../categories'

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
          <span className="label w-20 shrink-0">{monthLabel(m.key)}</span>
          <div className="flex flex-wrap gap-1">
            {m.days.map((d) => (
              <span
                key={d}
                aria-label={`${d}: ${covered.has(d) ? 'sales recorded' : 'no sales'}`}
                className={`h-4 w-4 rounded-[4px] ${covered.has(d) ? 'bg-accent' : 'bg-line'}`}
              />
            ))}
          </div>
        </div>
      ))}
      <p className="flex gap-5 pt-1 text-sm text-muted">
        <span className="flex items-center gap-1.5"><span className="h-3 w-3 rounded-[3px] bg-accent" />Sales recorded</span>
        <span className="flex items-center gap-1.5"><span className="h-3 w-3 rounded-[3px] bg-line" />None</span>
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

  if (error && !entries) return <p className="alert-error mx-5 mb-5">{error}</p>
  if (!entries) return <p className="card-body text-muted">Loading…</p>
  if (entries.length === 0) return <p className="empty mx-5 mb-5">No dishes were on the menu in this period.</p>

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
        <table className="table min-w-[480px]">
          <tbody>
            {groups.map(({ c, rows }) => [
              <tr key={`h-${c}`}>
                <th colSpan={2} className="pt-5">{c ? `${c}s` : 'No category'}</th>
              </tr>,
              ...rows.map((e) => (
                <tr key={e.dish_id}>
                  <td>
                    <span className="font-semibold">{e.dish_name}</span>
                    {e.other_records > 0 && <span className="chip chip-muted ml-2">Daily sales recorded</span>}
                  </td>
                  <td className="w-40 text-right">
                    <input
                      type="number" min="0" step="1" inputMode="numeric"
                      value={e.other_records > 0 ? '' : values[e.dish_id]}
                      placeholder={e.other_records > 0 ? '—' : 'units'}
                      disabled={e.other_records > 0}
                      onChange={(ev) => { setValues({ ...values, [e.dish_id]: ev.target.value }); setSaved(false) }}
                      className="input num w-28 py-1.5 text-right"
                      aria-label={`Units sold: ${e.dish_name}`}
                    />
                  </td>
                </tr>
              )),
            ])}
          </tbody>
        </table>
      </div>
      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-line bg-bg px-5 py-3.5">
        <Hint content="Every dish on the menu in this period is analysed, so a blank counts as 0 sold. If a dish wasn't on the menu, change its menu dates on its dish page."
              label="How blanks are counted" />
        <div className="flex items-center gap-3">
          {saved && <span className="text-sm font-semibold text-muted">Saved</span>}
          {error && <span className="text-sm text-danger">{error}</span>}
          <button type="button" onClick={save} disabled={saving || editable.length === 0} className="btn btn-primary">
            {saving ? 'Saving…' : 'Save sales'}
          </button>
        </div>
      </div>
    </div>
  )
}

function SalesPage({ range, coverage, onSaved }) {
  const salesImport = usePageImport('sales', 'Import sales', onSaved)
  if (salesImport.review) return salesImport.review

  const covered = coverage.days_with_sales.length
  return (
    <div className="space-y-6">
      <div className="flex justify-end">{salesImport.button}</div>
      {salesImport.error && <p className="alert-error">{salesImport.error}</p>}
      <SalesMoney range={range} coverage={coverage} />

      <Card title="Coverage" aside={<span className="num">{covered} of {daysBetween(range.from, range.to)} days</span>}>
        <CoverageStrip range={range} coverage={coverage} />
      </Card>

      <Card title={`Enter totals · ${rangeLabel(range)}`} flush>
        <ManualEntry range={range} onSaved={onSaved} />
      </Card>
    </div>
  )
}

export default SalesPage
