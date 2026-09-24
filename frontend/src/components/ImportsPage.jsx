import { useEffect, useRef, useState } from 'react'
import Card from './Card'
import ConfirmDialog from './ConfirmDialog'
import InvoiceReview from './InvoiceReview'
import SalesReview from './SalesReview'
import { getJson, postFile, postJson } from '../api'
import { shortDate } from '../format'

const KIND_LABELS = { invoice: 'Invoice', sales: 'Sales', menu: 'Menu' }

// Upload an invoice or a till export, check what Claude read, apply it; and
// the history of everything imported, with Undo.
function ImportsPage({ onChanged }) {
  const [imports, setImports] = useState(null)
  const [loads, setLoads] = useState(0)
  const [review, setReview] = useState(null)        // { kind, review, options } while checking a file (options: ingredients or dishes)
  const [reading, setReading] = useState(null)      // 'invoice' | 'sales' while a file is being read
  const [applied, setApplied] = useState(null)
  const [undoing, setUndoing] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const invoiceInput = useRef(null)
  const salesInput = useRef(null)

  useEffect(() => {
    let ignore = false
    getJson('/imports')
      .then((rows) => { if (!ignore) setImports(rows) })
      .catch((err) => { if (!ignore) setError(err.message) })
    return () => { ignore = true }
  }, [loads])

  // kind: 'invoice' (checked against the ingredient list) or 'sales' (against the dishes).
  const upload = (kind) => (e) => {
    const file = e.target.files[0]
    e.target.value = ''   // choosing the same file again still triggers a change
    if (!file) return
    setReading(kind)
    setError(null)
    setApplied(null)
    const [route, list] = kind === 'invoice' ? ['/imports/invoice/read', '/ingredients'] : ['/imports/sales/read', '/dishes']
    Promise.all([postFile(route, file), getJson(list)])
      .then(([r, options]) => setReview({ kind, review: r, options }))
      .catch((err) => setError(err.message))
      .finally(() => setReading(null))
  }

  const afterApply = (record) => {
    setReview(null)
    setApplied(record)
    setLoads((n) => n + 1)
    onChanged()   // prices or sales changed, so the figures did too
  }

  const undo = () => {
    setBusy(true)
    postJson(`/imports/${undoing.id}/undo`, {})
      .then(() => {
        setUndoing(null)
        setError(null)
        setApplied(null)
        setLoads((n) => n + 1)
        onChanged()
      })
      .catch((err) => {
        setUndoing(null)
        setError(err.message)
      })
      .finally(() => setBusy(false))
  }

  if (review?.kind === 'invoice') {
    return <InvoiceReview review={review.review} ingredients={review.options}
                          onApplied={afterApply} onCancel={() => setReview(null)} />
  }
  if (review?.kind === 'sales') {
    return <SalesReview initial={review.review} dishes={review.options}
                        onApplied={afterApply} onCancel={() => setReview(null)} />
  }

  const uploadButtons = (
    <div className="flex flex-wrap gap-2">
      <input ref={invoiceInput} type="file" accept=".pdf,.jpg,.jpeg,.png,.webp" className="sr-only"
             onChange={upload('invoice')} tabIndex={-1} aria-hidden="true" />
      <input ref={salesInput} type="file" accept=".csv" className="sr-only"
             onChange={upload('sales')} tabIndex={-1} aria-hidden="true" />
      <button type="button" onClick={() => invoiceInput.current.click()} disabled={reading !== null} className="btn btn-secondary">
        {reading === 'invoice' ? 'Reading invoice…' : 'Upload invoice'}
      </button>
      <button type="button" onClick={() => salesInput.current.click()} disabled={reading !== null} className="btn btn-secondary">
        {reading === 'sales' ? 'Reading sales…' : 'Upload sales'}
      </button>
    </div>
  )

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <span className="flex items-center gap-3 text-muted">
          {reading && <span className="h-4 w-4 animate-spin rounded-full border-2 border-line border-t-accent" aria-hidden="true" />}
          {applied && (
            <span className="chip chip-accent num">
              {applied.kind === 'sales'
                ? `${applied.lines_applied} daily totals saved`
                : `${applied.lines_applied} prices saved from ${applied.supplier}`}
            </span>
          )}
        </span>
        {uploadButtons}
      </div>
      {error && <p className="alert-error">{error}</p>}

      {!imports ? (
        <p className="text-muted">Loading…</p>
      ) : imports.length === 0 ? (
        <div className="empty">
          <p className="section-title text-ink">No imports yet</p>
        </div>
      ) : (
        <Card title="History" flush>
          <div className="overflow-x-auto">
            <table className="table">
              <thead>
                <tr>
                  <th>Imported</th>
                  <th>Type</th>
                  <th>Supplier</th>
                  <th>Reference</th>
                  <th>Dated</th>
                  <th className="text-right">Lines</th>
                  <th>Status</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {imports.map((i) => (
                  <tr key={i.id}>
                    <td className="num whitespace-nowrap">{shortDate(i.created_at)}</td>
                    <td>{KIND_LABELS[i.kind]}</td>
                    <td>{i.supplier ?? '–'}</td>
                    <td className="num">{i.reference ?? '–'}</td>
                    <td className="num whitespace-nowrap">
                      {shortDate(i.effective_date)}{i.period_end && i.period_end !== i.effective_date && ` – ${shortDate(i.period_end)}`}
                    </td>
                    <td className="num text-right">
                      {i.lines_applied}
                      {i.lines_ignored > 0 && <span className="text-muted"> + {i.lines_ignored} ignored</span>}
                    </td>
                    <td>
                      <span className={`chip ${i.status === 'applied' ? 'chip-accent' : 'chip-muted'}`}>
                        {i.status === 'applied' ? 'Applied' : 'Undone'}
                      </span>
                    </td>
                    <td className="text-right">
                      {i.status === 'applied' && i.kind !== 'menu' && (
                        <button type="button" onClick={() => setUndoing(i)} className="btn btn-secondary btn-sm">Undo</button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      <ConfirmDialog open={undoing !== null} title={undoing?.kind === 'sales' ? 'Undo these sales?' : 'Undo this invoice?'}
                     confirmLabel="Undo" busy={busy} onConfirm={undo} onCancel={() => setUndoing(null)}>
        {undoing?.kind === 'sales' &&
          `The ${undoing.lines_applied} daily totals from ${undoing.filename ?? 'this file'} are removed. Days it replaced from an earlier import don't come back; upload that file again to restore them.`}
        {undoing?.kind === 'invoice' &&
          `The ${undoing.lines_applied} prices from ${undoing.supplier} ${undoing.reference} are removed, and costs go back to the previous prices.`}
      </ConfirmDialog>
    </div>
  )
}

export default ImportsPage
