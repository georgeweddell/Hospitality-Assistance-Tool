import { useState } from 'react'
import Hint from './Hint'
import { daysBetween, presets, rangeLabel } from '../dateRange'

// Choose the period the analysis covers: a preset, or any custom range.
function RangePicker({ range, lastSale, onChange }) {
  const options = presets(lastSale)
  const [customOpen, setCustomOpen] = useState(false)   // the From/To boxes, open only while choosing
  const [from, setFrom] = useState(range.from)
  const [to, setTo] = useState(range.to)

  const choosePreset = (key) => {
    if (key === 'applied') return   // the custom range already chosen
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
    if (from && to && from <= to) {
      onChange({ key: 'custom', from, to })
      setCustomOpen(false)
    }
  }

  // One row, so the header's items stay in line. How complete the period's
  // sales are shows beside the page title instead (CoverageChips, below).
  return (
    <div className="flex flex-wrap items-center justify-end gap-2">
      <select
        value={customOpen ? 'custom' : range.key === 'custom' ? 'applied' : range.key}
        onChange={(e) => choosePreset(e.target.value)}
        className="input input-pill w-auto"
        aria-label="Period"
      >
        {options.map((o) => <option key={o.key} value={o.key}>{o.label}</option>)}
        {range.key === 'custom' && <option value="applied">{rangeLabel(range)}</option>}
        <option value="custom">{range.key === 'custom' ? 'Change dates…' : 'Custom range…'}</option>
      </select>
      {customOpen && (
        <form onSubmit={applyCustom} className="flex flex-wrap items-center gap-2">
          <input type="date" value={from} onChange={(e) => setFrom(e.target.value)} className="input w-auto" aria-label="From" />
          <span className="text-sm text-muted">to</span>
          <input type="date" value={to} min={from} onChange={(e) => setTo(e.target.value)} className="input w-auto" aria-label="To" />
          <button type="submit" disabled={!from || !to || from > to} className="btn btn-primary">Apply</button>
        </form>
      )}
    </div>
  )
}

// How complete the period's sales are, as chips for the page title row (not the
// header, which has no room): days with sales, and records left out.
export function CoverageChips({ range, coverage }) {
  const days = daysBetween(range.from, range.to)
  const covered = coverage?.days_with_sales.length ?? null
  return (
    <>
      {covered != null && covered < days && (
        <Hint align="right" content={`Sales are recorded on ${covered} of the ${days} days in this period.`}>
          <span className="chip chip-warn num">sales on {covered} of {days} days</span>
        </Hint>
      )}
      {coverage?.partial_records > 0 && (
        <Hint align="right" content="These sales records cover dates both inside and outside this period, so they aren't counted rather than being split across days.">
          <span className="chip chip-warn num">{coverage.partial_records} record{coverage.partial_records === 1 ? '' : 's'} not counted</span>
        </Hint>
      )}
    </>
  )
}

export default RangePicker
