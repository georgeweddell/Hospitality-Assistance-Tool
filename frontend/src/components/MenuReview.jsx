import { useState } from 'react'
import Card from './Card'
import Hint from './Hint'
import { postJson } from '../api'
import { CATEGORIES } from '../categories'
import { pounds, shortDate } from '../format'

// The order changes are listed in: questions first, then what will change.
const GROUPS = [
  ['renamed', 'Renamed?'],
  ['new', 'New'],
  ['returning', 'Back on the menu'],
  ['price', 'Price changes'],
  ['not_a_dish', 'Not dishes'],
  ['same', 'Unchanged'],
]
const HINTS = {
  renamed: 'Close to a dish on your menu now. Say whether it is that dish with a new name (its recipe, sales and prices stay with it) or a different dish.',
  returning: 'This dish came off the menu earlier. It comes back as a new record with the old recipe copied, so the months it was off stay correct.',
  check_recipe: 'The description has changed since the last menu. The dish is kept; check its recipe still matches.',
  before_sales: 'Sales from this date on are then analysed with these prices and menu dates.',
}

// A review item -> the editable line (inputs hold strings).
function toLine(item, key) {
  return { ...item, key, price: item.price == null ? '' : String(item.price), category: item.category ?? '' }
}

// "match:<dish id>" | "new" | "ignore" | "" (not answered yet)
function actionValue(line) {
  if (line.action === 'match') return `match:${line.dish_id}`
  return line.action ?? ''
}

function ActionSelect({ line, onChange }) {
  const set = (value) => {
    if (value.startsWith('match:')) onChange({ ...line, action: 'match', dish_id: Number(value.slice(6)) })
    else onChange({ ...line, action: value || null })
  }
  const options = []
  if (line.status === 'renamed') {
    options.push(['', 'Choose…'])
    for (const s of line.suggestions) options.push([`match:${s.id}`, `Same dish as ${s.name}`])
    options.push(['new', 'A new dish'])
  } else if (line.status === 'same' || line.status === 'price') {
    options.push([`match:${line.dish_id}`, line.status === 'price' ? 'Update price' : 'No change'])
  } else {
    options.push(['new', 'Add to menu'])
  }
  options.push(['ignore', 'Ignore'])
  return (
    <select aria-label={`Action for ${line.name}`} className="input w-52" value={actionValue(line)} onChange={(e) => set(e.target.value)}>
      {options.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
    </select>
  )
}

function Line({ line, onChange }) {
  const set = (field) => (e) => onChange({ ...line, [field]: e.target.value })
  const price = Number(line.price)
  const change = line.current_price && line.price !== '' && line.action === 'match'
    ? (price / line.current_price - 1) * 100 : null
  const ignored = line.action === 'ignore'
  return (
    <tr className={ignored ? 'text-muted' : undefined}>
      <td className="min-w-56">
        <input aria-label="Dish name" className="input" value={line.name} onChange={set('name')} />
        {(line.description || line.description_changed || line.remembered) && (
          <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
            {line.remembered && (
              <Hint content="You ignored this on an earlier menu.">
                <span className="chip chip-muted">Remembered</span>
              </Hint>
            )}
            {line.description_changed && (
              <Hint content={HINTS.check_recipe}>
                <span className="chip chip-warn">Check recipe</span>
              </Hint>
            )}
            {line.description && <span className="text-xs text-muted">{line.description}</span>}
          </div>
        )}
      </td>
      <td>
        <select aria-label="Category" className="input w-32" value={line.category} onChange={set('category')}
                disabled={line.action === 'match'}>
          <option value="">–</option>
          {CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
      </td>
      <td>
        <input aria-label="Price (£)" className="input num w-24" inputMode="decimal" value={line.price} onChange={set('price')} />
      </td>
      <td className="whitespace-nowrap text-sm text-muted">
        {line.current_name && line.current_name !== line.name && <span className="block">{line.current_name}</span>}
        {line.current_price != null && <span className="num">{pounds(line.current_price)}</span>}
        {change != null && Math.abs(change) >= 0.05 && (
          <span className="num ml-1.5 text-xs font-semibold">{change > 0 ? '▲' : '▼'}{Math.abs(change).toFixed(0)}%</span>
        )}
      </td>
      <td><ActionSelect line={line} onChange={onChange} /></td>
    </tr>
  )
}

// Checking a menu Claude has read, before anything changes.
function MenuReview({ initial, onApplied, onCancel }) {
  const [review, setReview] = useState(initial)
  const [lines, setLines] = useState(() => initial.items.map(toLine))
  const [keep, setKeep] = useState(() => new Set())   // leaving dishes the owner keeps on the menu
  const [showSame, setShowSame] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  const updateLine = (changed) => setLines((ls) => ls.map((l) => (l.key === changed.key ? changed : l)))

  // A new start date changes what counts as current, so compare again (no AI call).
  // The owner's edits to names, prices and categories are kept; answers are asked again.
  const changeStart = (startDate) => {
    if (!startDate) return
    setBusy(true)
    setError(null)
    postJson('/imports/menu/review', {
      start_date: startDate,
      filename: initial.filename,
      file_hash: initial.file_hash,
      items: lines.map((l) => ({ ...l, price: l.price === '' ? null : Number(l.price), category: l.category || null })),
    })
      .then((r) => {
        setReview(r)
        setLines(r.items.map(toLine))
        setKeep(new Set())
      })
      .catch((err) => setError(err.message))
      .finally(() => setBusy(false))
  }

  const matchedIds = new Set(lines.filter((l) => l.action === 'match').map((l) => l.dish_id))
  const leaving = review.leaving.filter((d) => !matchedIds.has(d.dish_id))   // a confirmed rename isn't leaving
  const unanswered = lines.filter((l) => l.action == null).length

  const apply = () => {
    if (unanswered) {
      setError('Answer each "Renamed?" line first.')
      return
    }
    setBusy(true)
    setError(null)
    postJson('/imports/menu/apply', {
      start_date: review.start_date,
      filename: initial.filename,
      file_hash: initial.file_hash,
      items: lines.map((l) => ({
        name: l.name.trim(), price: l.price === '' ? null : Number(l.price), category: l.category || null,
        description: l.description, action: l.action, dish_id: l.action === 'match' ? l.dish_id : null,
        copy_from: l.action === 'new' ? l.copy_from : null,
      })),
      take_off: leaving.filter((d) => !keep.has(d.dish_id)).map((d) => d.dish_id),
    })
      .then(onApplied)
      .catch((err) => {
        setError(err.message)
        setBusy(false)
      })
  }

  const counts = Object.fromEntries(GROUPS.map(([status]) => [status, lines.filter((l) => l.status === status).length]))
  const beforeSales = review.latest_sale && review.start_date <= review.latest_sale

  return (
    <div className="space-y-5">
      <Card title="Menu" aside={initial.filename}>
        <div className="flex flex-wrap items-end gap-4">
          <label className="field">
            <span className="label">Starts on</span>
            <input type="date" className="input w-44" value={review.start_date}
                   onChange={(e) => changeStart(e.target.value)} disabled={busy} />
          </label>
          <span className="flex flex-wrap gap-1.5 pb-2">
            {review.already_imported && <span className="chip chip-warn">Already imported</span>}
            {beforeSales && (
              <Hint content={HINTS.before_sales}>
                <span className="chip chip-warn">Before your latest sale ({shortDate(review.latest_sale)})</span>
              </Hint>
            )}
            {counts.new > 0 && <span className="chip chip-accent num">{counts.new} new</span>}
            {counts.returning > 0 && <span className="chip chip-accent num">{counts.returning} back</span>}
            {counts.price > 0 && <span className="chip chip-accent num">{counts.price} price changes</span>}
            {counts.renamed > 0 && <span className="chip chip-warn num">{counts.renamed} renamed?</span>}
            {leaving.length > 0 && <span className="chip chip-muted num">{leaving.length} coming off</span>}
            <span className="chip chip-muted num">{counts.same} unchanged</span>
          </span>
        </div>
      </Card>

      {GROUPS.map(([status, title]) => {
        const group = lines.filter((l) => l.status === status)
        if (group.length === 0) return null
        const folded = status === 'same' && !showSame
        return (
          <Card key={status} flush
                title={<span className="flex items-center gap-2">{title}{HINTS[status] && <Hint content={HINTS[status]} />}</span>}
                aside={status === 'same' && (
                  <button type="button" className="link text-sm" onClick={() => setShowSame((s) => !s)}>
                    {showSame ? 'Hide' : `Show ${group.length}`}
                  </button>
                )}>
            {!folded && (
              <div className="overflow-x-auto">
                <table className="table min-w-[860px] table-fixed">
                  <colgroup>
                    <col />
                    <col className="w-40" />
                    <col className="w-32" />
                    <col className="w-44" />
                    <col className="w-60" />
                  </colgroup>
                  <thead>
                    <tr><th>Dish</th><th>Category</th><th>Price</th><th>Now</th><th>Action</th></tr>
                  </thead>
                  <tbody>
                    {group.map((line) => <Line key={line.key} line={line} onChange={updateLine} />)}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        )
      })}

      {leaving.length > 0 && (
        <Card title="Coming off the menu" flush>
          <ul className="divide-y divide-line border-t border-line">
            {leaving.map((d) => (
              <li key={d.dish_id} className="flex items-center justify-between gap-3 px-5 py-3">
                <span>
                  <span className="font-semibold">{d.name}</span>
                  <span className="ml-2 text-sm text-muted">{d.category ?? ''}{d.price != null && ` · ${pounds(d.price)}`}</span>
                </span>
                <label className="flex items-center gap-2 text-sm">
                  <input type="checkbox" checked={!keep.has(d.dish_id)}
                         onChange={(e) => setKeep((k) => {
                           const next = new Set(k)
                           if (e.target.checked) next.delete(d.dish_id)
                           else next.add(d.dish_id)
                           return next
                         })} />
                  Take off
                </label>
              </li>
            ))}
          </ul>
        </Card>
      )}

      {error && <p className="alert-error">{error}</p>}
      <div className="flex items-center justify-end gap-3">
        {busy && <span className="h-4 w-4 animate-spin rounded-full border-2 border-line border-t-accent" aria-hidden="true" />}
        <button type="button" onClick={onCancel} disabled={busy} className="btn btn-secondary">Cancel</button>
        <button type="button" onClick={apply} disabled={busy} className="btn btn-primary">Apply</button>
      </div>
    </div>
  )
}

export default MenuReview
