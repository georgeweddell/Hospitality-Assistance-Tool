import { useMemo, useRef, useState } from 'react'
import Card from './Card'
import Hint from './Hint'
import { postJson } from '../api'
import { shortDate } from '../format'

// Each date format shown as an example date, which explains itself.
const DATE_FORMATS = [
  ['%d/%m/%Y', '18/09/2026'],
  ['%Y-%m-%d', '2026-09-18'],
  ['%m/%d/%Y', '09/18/2026'],
  ['%d-%m-%Y', '18-09-2026'],
  ['%d.%m.%Y', '18.09.2026'],
  ['%d/%m/%y', '18/09/26'],
]
const EMPTY_MAPPING = { date_column: '', item_column: '', quantity_column: '', date_format: '%d/%m/%Y', refund_column: '', refund_value: '' }

const FLAG_CHIPS = {
  choose: () => ['chip-warn', 'Choose a dish', 'Not matched to a dish yet. Choose one, or Ignore.'],
  off_menu: () => ['chip-warn', 'Off the menu', "Some of these sales fall outside the dish's menu dates. They're still saved; check the dates on the dish page."],
  conflict: (it) => ['chip-warn', `${it.conflict_days} days skipped`, 'Sales for these days were already entered another way (e.g. a typed total), so these are skipped rather than counted twice.'],
  replaces: (it) => ['chip-muted', `Replaces ${it.replace_days} days`, 'These days came from an earlier till import. The figures in this file replace them.'],
}

function mappingComplete(m) {
  return m.date_column && m.item_column && m.quantity_column && m.date_format
}

// The body the review and apply routes expect for a mapping.
function mappingBody(m) {
  return { ...m, refund_column: m.refund_column || null, refund_value: m.refund_column ? m.refund_value || null : null }
}

function ColumnSelect({ label, value, header, onChange, blank = 'Choose…' }) {
  return (
    <label className="field">
      <span className="label">{label}</span>
      <select className="input" value={value} onChange={(e) => onChange(e.target.value)}>
        <option value="">{blank}</option>
        {header.map((h) => <option key={h} value={h}>{h}</option>)}
      </select>
    </label>
  )
}

// Checking a till export before its sales are saved.
function SalesReview({ initial, dishes, onApplied, onCancel }) {
  const [review, setReview] = useState(initial)
  const [mapping, setMapping] = useState(() => (initial.mapping
    ? { ...EMPTY_MAPPING, ...initial.mapping, refund_column: initial.mapping.refund_column ?? '', refund_value: initial.mapping.refund_value ?? '' }
    : EMPTY_MAPPING))
  // The owner's choice per item, starting from the first review (which includes Claude's suggestions).
  const [choices, setChoices] = useState(() => Object.fromEntries(initial.items.map((it) => [it.item, { action: it.action, dish_id: it.dish_id }])))
  // What Claude said each item is ("other" = drink, add-on...): only known from the first review.
  const [kinds] = useState(() => Object.fromEntries(initial.items.map((it) => [it.item, it.kind])))
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const typing = useRef(null)   // timer: re-read once the owner stops typing the refund value

  const sortedDishes = useMemo(() => [...dishes].sort((a, b) => a.name.localeCompare(b.name)), [dishes])

  // Re-reads the file on the server with these columns and choices.
  const refresh = (nextMapping, nextChoices) => {
    if (!mappingComplete(nextMapping)) return
    setBusy(true)
    setError(null)
    postJson('/imports/sales/review', {
      file_hash: initial.file_hash,
      filename: initial.filename,
      mapping: mappingBody(nextMapping),
      choices: Object.entries(nextChoices).map(([item, c]) => ({ item, ...c })),
    })
      .then((r) => {
        setReview(r)
        // Items new to this reading (e.g. after changing the item column) start as the server suggests.
        setChoices((current) => {
          const merged = { ...current }
          for (const it of r.items) if (!(it.item in merged)) merged[it.item] = { action: it.action, dish_id: it.dish_id }
          return merged
        })
      })
      .catch((err) => setError(err.message))
      .finally(() => setBusy(false))
  }

  const setColumn = (field) => (value) => {
    const next = { ...mapping, [field]: value }
    setMapping(next)
    refresh(next, choices)
  }

  const setRefundValue = (value) => {
    const next = { ...mapping, refund_value: value }
    setMapping(next)
    clearTimeout(typing.current)
    typing.current = setTimeout(() => refresh(next, choices), 500)
  }

  const choose = (item, value) => {
    const choice = value === 'ignore' ? { action: 'ignore', dish_id: null }
      : { action: 'dish', dish_id: value ? Number(value) : null }
    const next = { ...choices, [item]: choice }
    setChoices(next)
    refresh(mapping, next)
  }

  const apply = () => {
    setBusy(true)
    setError(null)
    postJson('/imports/sales/apply', {
      file_hash: initial.file_hash,
      filename: initial.filename,
      mapping: mappingBody(mapping),
      choices: review.items.map((it) => ({ item: it.item, ...(choices[it.item] ?? { action: it.action, dish_id: it.dish_id }) })),
    })
      .then(onApplied)
      .catch((err) => {
        setError(err.message)
        setBusy(false)
      })
  }

  const skippedRows = Object.values(review.skipped).reduce((a, b) => a + b, 0)
  const ready = mappingComplete(mapping) && review.items.length > 0

  return (
    <div className="space-y-5">
      <Card
        title="Columns"
        aside={
          <span className="flex flex-wrap items-center gap-1.5">
            {review.mapping_remembered && <span className="chip chip-muted">Remembered</span>}
            {review.ai_unavailable && (
              <Hint align="right" content="The AI service couldn't be reached, so choose the columns yourself.">
                <span className="chip chip-warn">AI unavailable</span>
              </Hint>
            )}
            <span>{initial.filename}</span>
          </span>
        }
      >
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
          <ColumnSelect label="Date" value={mapping.date_column} header={review.header} onChange={setColumn('date_column')} />
          <label className="field">
            <span className="label">Dates look like</span>
            <select className="input" value={mapping.date_format} onChange={(e) => setColumn('date_format')(e.target.value)}>
              {DATE_FORMATS.map(([value, example]) => <option key={value} value={value}>{example}</option>)}
            </select>
          </label>
          <ColumnSelect label="Item" value={mapping.item_column} header={review.header} onChange={setColumn('item_column')} />
          <ColumnSelect label="Quantity" value={mapping.quantity_column} header={review.header} onChange={setColumn('quantity_column')} />
          <div className="grid grid-cols-[1fr_auto] items-end gap-2">
            <ColumnSelect label="Refunds marked in" value={mapping.refund_column} header={review.header}
                          onChange={setColumn('refund_column')} blank="Negative quantities" />
            {mapping.refund_column && (
              <input aria-label="Refund value" className="input w-24" value={mapping.refund_value}
                     onChange={(e) => setRefundValue(e.target.value)} />
            )}
          </div>
        </div>

        <div className="mt-5 overflow-x-auto rounded-[10px] border border-line">
          <table className="table text-xs">
            <thead>
              <tr>{review.header.map((h) => <th key={h}>{h}</th>)}</tr>
            </thead>
            <tbody>
              {review.samples.map((row, i) => (
                <tr key={i}>{review.header.map((h, j) => <td key={h} className="whitespace-nowrap py-2">{row[j]}</td>)}</tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {mappingComplete(mapping) && (
        <Card
          title="Items"
          flush
          aside={
            <span className="flex flex-wrap items-center justify-end gap-1.5">
              {review.already_imported && (
                <Hint align="right" content="This file has been imported before. Undo that import on the Imports page to import it again.">
                  <span className="chip chip-warn">Already imported</span>
                </Hint>
              )}
              {review.first_date && (
                <span className="chip chip-muted num">{shortDate(review.first_date)} – {shortDate(review.last_date)}</span>
              )}
              <span className="chip chip-accent num">{review.units.toLocaleString('en-GB')} sold</span>
              <span className="chip chip-accent num">{review.dish_days} daily totals</span>
              {review.replace_days > 0 && <span className="chip chip-muted num">{review.replace_days} replaced</span>}
              {review.conflict_days > 0 && <span className="chip chip-warn num">{review.conflict_days} skipped</span>}
              {skippedRows > 0 && (
                <Hint align="right" content={Object.entries(review.skipped).map(([reason, n]) => `${reason}: ${n}`).join(' · ')}>
                  <span className="chip chip-warn num">{skippedRows} rows unreadable</span>
                </Hint>
              )}
            </span>
          }
        >
          <div className="overflow-x-auto">
            <table className="table">
              <thead>
                <tr>
                  <th>Till item</th>
                  <th className="text-right">Sold</th>
                  <th className="text-right">Days</th>
                  <th>Dish</th>
                </tr>
              </thead>
              <tbody>
                {review.items.map((it) => {
                  const choice = choices[it.item] ?? { action: it.action, dish_id: it.dish_id }
                  const ignored = choice.action === 'ignore'
                  return (
                    <tr key={it.item} className={ignored ? 'text-muted' : undefined}>
                      <td>
                        <p className="font-medium">{it.item}</p>
                        {(it.remembered || kinds[it.item] === 'other' || it.flags.length > 0) && (
                          <div className="mt-1.5 flex flex-wrap gap-1.5">
                            {it.remembered && (
                              <Hint content="You matched this item on an earlier import.">
                                <span className="chip chip-muted">Remembered</span>
                              </Hint>
                            )}
                            {kinds[it.item] === 'other' && !it.remembered && (
                              <Hint content="Looks like a drink, add-on or charge rather than a dish, so it's ignored.">
                                <span className="chip chip-muted">Not a dish</span>
                              </Hint>
                            )}
                            {it.flags.map((f) => {
                              const [tone, label, hint] = FLAG_CHIPS[f](it)
                              return (
                                <Hint key={f} content={hint}>
                                  <span className={`chip ${tone}`}>{label}</span>
                                </Hint>
                              )
                            })}
                          </div>
                        )}
                      </td>
                      <td className="num text-right">{it.units}</td>
                      <td className="num text-right">{it.days}</td>
                      <td className="min-w-56">
                        <select aria-label={`Dish for ${it.item}`} className="input"
                                value={ignored ? 'ignore' : choice.dish_id ?? ''}
                                onChange={(e) => choose(it.item, e.target.value)}>
                          <option value="">Choose…</option>
                          <option value="ignore">Ignore</option>
                          {sortedDishes.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
                        </select>
                        {!ignored && choice.dish_id == null && it.suggestions.length > 0 && (
                          <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
                            <span className="text-xs text-muted">Or use:</span>
                            {it.suggestions.map((s) => (
                              <button key={s.id} type="button" className="chip chip-accent" onClick={() => choose(it.item, s.id)}>
                                {s.name}
                              </button>
                            ))}
                          </div>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {error && <p className="alert-error">{error}</p>}
      <div className="flex items-center justify-end gap-3">
        {busy && <span className="h-4 w-4 animate-spin rounded-full border-2 border-line border-t-accent" aria-hidden="true" />}
        <button type="button" onClick={onCancel} disabled={busy} className="btn btn-secondary">Cancel</button>
        <button type="button" onClick={apply} disabled={busy || !ready} className="btn btn-primary">Apply</button>
      </div>
    </div>
  )
}

export default SalesReview
