import { useMemo, useState } from 'react'
import Card from './Card'
import Hint from './Hint'
import { postJson } from '../api'
import { pounds, priceForDisplay } from '../format'
import { FLAGS, PACK_UNIT_OPTIONS, applyLine, changePercent, lineFlags, linePrice, lineUnit, toEditable } from '../invoices'

const ACTIONS = [['update', 'Update price'], ['new', 'New ingredient'], ['ignore', 'Ignore']]

function Change({ percent }) {
  if (percent == null || Math.abs(percent) < 0.05) return null
  return <span className="num text-xs font-semibold text-muted">{percent > 0 ? '▲' : '▼'}{Math.abs(percent).toFixed(0)}%</span>
}

function Line({ line, ingredients, byId, onChange }) {
  const set = (field) => (e) => onChange({ ...line, [field]: e.target.value })
  const ingredient = line.action === 'update' ? byId.get(Number(line.ingredient_id)) : null
  const unit = lineUnit(line, ingredient)
  const price = linePrice(line, unit)
  const flags = lineFlags(line, ingredient)
  const ignored = line.action === 'ignore'

  return (
    <tr className={ignored ? 'text-muted' : undefined}>
      <td className="min-w-44">
        <p className="font-medium">{line.description}</p>
        {(line.remembered || flags.length > 0) && (
          <div className="mt-1.5 flex flex-wrap gap-1.5">
            {line.remembered && (
              <Hint content="You matched this line on an earlier invoice from this supplier.">
                <span className="chip chip-muted">Remembered</span>
              </Hint>
            )}
            {flags.map((f) => (
              <Hint key={f} content={FLAGS[f][1]}>
                <span className="chip chip-warn">{FLAGS[f][0]}</span>
              </Hint>
            ))}
          </div>
        )}
      </td>
      <td>
        <div className="flex items-center gap-1">
          <input aria-label="Pack count" className="input num w-12 px-2" inputMode="decimal"
                 value={line.pack_count} onChange={set('pack_count')} />
          <span className="text-muted">×</span>
          <input aria-label="Pack size" className="input num w-14 px-2" inputMode="decimal"
                 value={line.pack_size} onChange={set('pack_size')} />
          <select aria-label="Pack unit" className="input w-[4.5rem] px-2" value={line.pack_unit} onChange={set('pack_unit')}>
            <option value="">–</option>
            {PACK_UNIT_OPTIONS.map((u) => <option key={u} value={u}>{u}</option>)}
          </select>
        </div>
      </td>
      <td>
        <input aria-label="Unit price (£)" className="input num w-20 px-2" inputMode="decimal"
               value={line.unit_price} onChange={set('unit_price')} />
      </td>
      <td className="num whitespace-nowrap">
        {line.quantity ?? '–'}
        <span className="block text-xs text-muted">{line.line_total != null ? pounds(line.line_total) : ''}</span>
      </td>
      <td>
        <select aria-label="Action" className="input w-40" value={line.action} onChange={set('action')}>
          {ACTIONS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </select>
      </td>
      <td className="min-w-48">
        {line.action === 'update' && (
          <select aria-label="Ingredient" className="input" value={line.ingredient_id ?? ''}
                  onChange={(e) => onChange({ ...line, ingredient_id: e.target.value ? Number(e.target.value) : null })}>
            <option value="">Choose…</option>
            {ingredients.map((i) => <option key={i.id} value={i.id}>{i.name}</option>)}
          </select>
        )}
        {line.action === 'new' && (
          <>
            <input aria-label="New ingredient name" className="input" value={line.new_ingredient_name}
                   onChange={set('new_ingredient_name')} />
            {line.suggestions.length > 0 && (
              <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
                <span className="text-xs text-muted">Or use:</span>
                {line.suggestions.map((s) => (
                  <button key={s.id} type="button" className="chip chip-accent"
                          onClick={() => onChange({ ...line, action: 'update', ingredient_id: s.id })}>
                    {s.name}
                  </button>
                ))}
              </div>
            )}
          </>
        )}
      </td>
      <td className="whitespace-nowrap text-right">
        {!ignored && price != null && (
          <>
            <span className="num font-semibold">{priceForDisplay(price, unit)}</span>
            <span className="block"><Change percent={changePercent(price, ingredient)} /></span>
          </>
        )}
      </td>
    </tr>
  )
}

// Checking an invoice Claude has read, before anything is saved.
function InvoiceReview({ review, ingredients, onApplied, onCancel }) {
  const [supplier, setSupplier] = useState(review.supplier ?? '')
  const [number, setNumber] = useState(review.invoice_number ?? '')
  const [invoiceDate, setInvoiceDate] = useState(review.invoice_date ?? '')
  const [lines, setLines] = useState(() => review.lines.map(toEditable))
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)

  const sorted = useMemo(() => [...ingredients].sort((a, b) => a.name.localeCompare(b.name)), [ingredients])
  const byId = useMemo(() => new Map(ingredients.map((i) => [i.id, i])), [ingredients])

  const counts = { update: 0, new: 0, ignore: 0 }
  let toCheck = 0
  for (const line of lines) {
    counts[line.action] += 1
    const ingredient = line.action === 'update' ? byId.get(Number(line.ingredient_id)) : null
    if (lineFlags(line, ingredient).length > 0) toCheck += 1
  }

  const updateLine = (changed) => setLines((ls) => ls.map((l) => (l.key === changed.key ? changed : l)))

  const apply = () => {
    if (!supplier.trim() || !number.trim() || !invoiceDate) {
      setError('Enter the supplier, invoice number and date.')
      return
    }
    setSaving(true)
    setError(null)
    postJson('/imports/invoice/apply', {
      supplier: supplier.trim(),
      invoice_number: number.trim(),
      invoice_date: invoiceDate,
      filename: review.filename,
      file_hash: review.file_hash,
      lines: lines.map(applyLine),
    })
      .then(onApplied)
      .catch((err) => {
        setError(err.message)
        setSaving(false)
      })
  }

  return (
    <div className="space-y-5">
      <Card title="Invoice" aside={review.filename}>
        <div className="grid gap-4 sm:grid-cols-3">
          <label className="field">
            <span className="label">Supplier</span>
            <input className="input" value={supplier} onChange={(e) => setSupplier(e.target.value)} />
          </label>
          <label className="field">
            <span className="label">Invoice number</span>
            <input className="input" value={number} onChange={(e) => setNumber(e.target.value)} />
          </label>
          <label className="field">
            <span className="label">Invoice date</span>
            <input type="date" className="input" value={invoiceDate} onChange={(e) => setInvoiceDate(e.target.value)} />
          </label>
        </div>
        {(review.already_imported || review.prices_include_vat) && (
          <div className="mt-4 flex flex-wrap gap-2">
            {review.already_imported && (
              <Hint content="This invoice has been imported before. Undo that import on the Imports page to import it again.">
                <span className="chip chip-warn">Already imported</span>
              </Hint>
            )}
            {review.prices_include_vat && (
              <Hint content="The prices on this invoice include VAT. Ingredient prices are stored excluding VAT, so enter the ex-VAT unit prices.">
                <span className="chip chip-warn">Prices include VAT</span>
              </Hint>
            )}
          </div>
        )}
      </Card>

      <Card
        title="Lines"
        flush
        aside={
          <span className="flex flex-wrap gap-1.5">
            <span className="chip chip-accent num">{counts.update} update</span>
            <span className="chip chip-accent num">{counts.new} new</span>
            <span className="chip chip-muted num">{counts.ignore} ignored</span>
            {toCheck > 0 && <span className="chip chip-warn num">{toCheck} to check</span>}
          </span>
        }
      >
        <div className="overflow-x-auto">
          <table className="table">
            <thead>
              <tr>
                <th>As printed</th>
                <th>Pack</th>
                <th>Unit price</th>
                <th>Qty</th>
                <th>Action</th>
                <th>Ingredient</th>
                <th className="text-right">New price</th>
              </tr>
            </thead>
            <tbody>
              {lines.map((line) => (
                <Line key={line.key} line={line} ingredients={sorted} byId={byId} onChange={updateLine} />
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {error && <p className="alert-error">{error}</p>}
      <div className="flex justify-end gap-2">
        <button type="button" onClick={onCancel} disabled={saving} className="btn btn-secondary">Cancel</button>
        <button type="button" onClick={apply} disabled={saving} className="btn btn-primary">
          {saving ? 'Saving…' : 'Apply'}
        </button>
      </div>
    </div>
  )
}

export default InvoiceReview
