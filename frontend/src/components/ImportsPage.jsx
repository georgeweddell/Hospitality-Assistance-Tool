import { useEffect, useRef, useState } from 'react'
import Card from './Card'
import ConfirmDialog from './ConfirmDialog'
import InvoiceReview from './InvoiceReview'
import { getJson, postFile, postJson } from '../api'
import { shortDate } from '../format'

const KIND_LABELS = { invoice: 'Invoice', sales: 'Sales', menu: 'Menu' }

// Upload an invoice, check what Claude read, apply it; and the history of
// everything imported, with Undo.
function ImportsPage({ onChanged }) {
  const [imports, setImports] = useState(null)
  const [loads, setLoads] = useState(0)
  const [review, setReview] = useState(null)        // { review, ingredients } while checking an invoice
  const [reading, setReading] = useState(false)
  const [applied, setApplied] = useState(null)
  const [undoing, setUndoing] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const fileInput = useRef(null)

  useEffect(() => {
    let ignore = false
    getJson('/imports')
      .then((rows) => { if (!ignore) setImports(rows) })
      .catch((err) => { if (!ignore) setError(err.message) })
    return () => { ignore = true }
  }, [loads])

  const upload = (e) => {
    const file = e.target.files[0]
    e.target.value = ''   // choosing the same file again still triggers a change
    if (!file) return
    setReading(true)
    setError(null)
    setApplied(null)
    Promise.all([postFile('/imports/invoice/read', file), getJson('/ingredients')])
      .then(([r, ingredients]) => setReview({ review: r, ingredients }))
      .catch((err) => setError(err.message))
      .finally(() => setReading(false))
  }

  const afterApply = (record) => {
    setReview(null)
    setApplied(record)
    setLoads((n) => n + 1)
    onChanged()   // prices changed, so dish costs did too
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

  if (review) {
    return <InvoiceReview review={review.review} ingredients={review.ingredients}
                          onApplied={afterApply} onCancel={() => setReview(null)} />
  }

  const uploadButton = (
    <>
      <input ref={fileInput} type="file" accept=".pdf,.jpg,.jpeg,.png,.webp" className="sr-only"
             onChange={upload} tabIndex={-1} aria-hidden="true" />
      <button type="button" onClick={() => fileInput.current.click()} disabled={reading} className="btn btn-primary">
        {reading ? 'Reading invoice…' : 'Upload invoice'}
      </button>
    </>
  )

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <span className="flex items-center gap-3 text-muted">
          {reading && <span className="h-4 w-4 animate-spin rounded-full border-2 border-line border-t-accent" aria-hidden="true" />}
          {applied && <span className="chip chip-accent num">{applied.lines_applied} prices saved from {applied.supplier}</span>}
        </span>
        {uploadButton}
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
                    <td className="num whitespace-nowrap">{shortDate(i.effective_date)}</td>
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
                      {i.status === 'applied' && i.kind === 'invoice' && (
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

      <ConfirmDialog open={undoing !== null} title="Undo this invoice?" confirmLabel="Undo" busy={busy}
                     onConfirm={undo} onCancel={() => setUndoing(null)}>
        {undoing && `The ${undoing.lines_applied} prices from ${undoing.supplier} ${undoing.reference} are removed, and costs go back to the previous prices.`}
      </ConfirmDialog>
    </div>
  )
}

export default ImportsPage
