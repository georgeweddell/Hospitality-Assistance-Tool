import { useState } from 'react'
import { daysBetween, presets, rangeLabel } from '../dateRange'

const INPUT = 'rounded-lg border border-line bg-surface px-3 py-2 text-sm text-ink focus:border-accent focus:outline-none'

// Choose the period the analysis covers: a preset, or any custom range.
function RangePicker({ range, lastSale, coverage, onChange }) {
  const options = presets(lastSale)
  const [customOpen, setCustomOpen] = useState(range.key === 'custom')
  const [from, setFrom] = useState(range.from)
  const [to, setTo] = useState(range.to)

  const choosePreset = (key) => {
    if (key === 'custom') {
      setFrom(range.from)
      setTo(range.to)
      setCustomOpen(true)
      return
    }
    setCustomOpen(false)
    const p = options.find((o) => o.key === key)
    onChange({ key, from: p.from, to: p.to })
  }

  const applyCustom = (e) => {
    e.preventDefault()
    if (from && to && from <= to) onChange({ key: 'custom', from, to })
  }

  const days = daysBetween(range.from, range.to)
  const covered = coverage?.days_with_sales.length ?? null

  return (
    <div className="flex flex-col items-start gap-1.5 sm:items-end">
      <div className="flex flex-wrap items-center gap-2">
        <select
          value={customOpen ? 'custom' : range.key}
          onChange={(e) => choosePreset(e.target.value)}
          className={INPUT}
          aria-label="Period"
        >
          {options.map((o) => <option key={o.key} value={o.key}>{o.label}</option>)}
          <option value="custom">Custom range…</option>
        </select>
        {customOpen && (
          <form onSubmit={applyCustom} className="flex flex-wrap items-center gap-2">
            <input type="date" value={from} onChange={(e) => setFrom(e.target.value)} className={INPUT} aria-label="From" />
            <span className="text-sm text-muted">to</span>
            <input type="date" value={to} min={from} onChange={(e) => setTo(e.target.value)} className={INPUT} aria-label="To" />
            <button type="submit" disabled={!from || !to || from > to}
                    className="rounded-lg bg-accent px-3 py-2 text-sm font-medium text-accent-ink hover:opacity-90 disabled:opacity-50">
              Apply
            </button>
          </form>
        )}
      </div>
      <p className="text-xs text-muted">
        {rangeLabel(range)}
        {covered != null && <> · sales on {covered} of {days} days</>}
      </p>
      {coverage?.partial_records > 0 && (
        <p className="text-xs text-warn">
          {coverage.partial_records} sales record{coverage.partial_records === 1 ? '' : 's'} only partly
          overlap this period and aren't counted.
        </p>
      )}
    </div>
  )
}

export default RangePicker
