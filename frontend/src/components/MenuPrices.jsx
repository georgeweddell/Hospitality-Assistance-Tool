import { useState } from 'react'
import Card from './Card'
import ConfirmDialog from './ConfirmDialog'
import { deleteJson } from '../api'
import { pounds, shortDate } from '../format'

// A dish's menu price history, newest first. The price in effect today is
// bold; one starting later is marked Upcoming. A price entered by mistake can
// be removed (the backend keeps at least one).
function MenuPrices({ dishId, prices, onChanged }) {
  const [removing, setRemoving] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  const today = new Date().toISOString().slice(0, 10)
  const current = prices.find((p) => p.effective_date <= today) ?? prices[prices.length - 1]

  const remove = () => {
    setBusy(true)
    deleteJson(`/dishes/${dishId}/prices/${removing.id}`)
      .then(() => {
        setRemoving(null)
        setError(null)
        onChanged()
      })
      .catch((err) => {
        setRemoving(null)
        setError(err.message)
      })
      .finally(() => setBusy(false))
  }

  return (
    <Card title="Menu prices" flush>
      <ul className="divide-y divide-line border-t border-line">
        {prices.map((p) => (
          <li key={p.id} className="flex items-center justify-between gap-3 px-5 py-2.5">
            <span className="num">From {shortDate(p.effective_date)}</span>
            <span className="flex items-center gap-2">
              {p.effective_date > today && <span className="chip chip-muted">Upcoming</span>}
              <span className={`num ${p === current ? 'font-semibold' : 'text-muted'}`}>{pounds(p.price)}</span>
              <button type="button" onClick={() => setRemoving(p)} aria-label={`Remove price from ${shortDate(p.effective_date)}`}
                      className="btn-icon">×</button>
            </span>
          </li>
        ))}
      </ul>
      {error && <p className="alert-error m-5">{error}</p>}

      <ConfirmDialog open={removing !== null} title="Remove this price?" confirmLabel="Remove" busy={busy}
                     onConfirm={remove} onCancel={() => setRemoving(null)}>
        {removing && `${pounds(removing.price)} from ${shortDate(removing.effective_date)}. The price before it applies instead.`}
      </ConfirmDialog>
    </Card>
  )
}

export default MenuPrices
