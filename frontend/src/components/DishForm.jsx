import { useState } from 'react'
import { CATEGORIES } from '../categories'

const INPUT = 'w-full rounded-lg border border-line bg-surface px-3 py-2 text-ink focus:border-accent focus:outline-none'

// Name, price and category. Used to add a dish and to edit one.
function DishForm({ initial = {}, submitLabel, onSubmit, onCancel }) {
  const [name, setName] = useState(initial.name ?? '')
  const [menuPrice, setMenuPrice] = useState(initial.menu_price != null ? String(initial.menu_price) : '')
  const [category, setCategory] = useState(initial.category ?? '')
  const [onMenuFrom, setOnMenuFrom] = useState(initial.on_menu_from ?? new Date().toISOString().slice(0, 10))
  const [onMenuUntil, setOnMenuUntil] = useState(initial.on_menu_until ?? '')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState(null)

  const handleSubmit = (e) => {
    e.preventDefault()

    if (name.trim() === '' || !(Number(menuPrice) > 0)) {
      setError('Enter a name and a menu price above £0.')
      return
    }
    if (!onMenuFrom || (onMenuUntil && onMenuUntil < onMenuFrom)) {
      setError("Enter when the dish went on the menu, and an end date that isn't before it.")
      return
    }

    setSubmitting(true)
    setError(null)
    onSubmit({
      name: name.trim(),
      menu_price: Number(menuPrice),
      category: category || null,
      on_menu_from: onMenuFrom,
      on_menu_until: onMenuUntil || null,
    })
      .catch((err) => {
        setError(err.message)
        setSubmitting(false)
      })
  }

  return (
    <form onSubmit={handleSubmit} className="grid gap-3 sm:grid-cols-[2fr_1fr_1fr_auto] sm:items-start">
      <label className="text-sm">
        <span className="mb-1 block text-muted">Dish name</span>
        <input type="text" value={name} onChange={(e) => setName(e.target.value)} className={INPUT} autoFocus />
      </label>
      <label className="text-sm">
        <span className="mb-1 block text-muted">Menu price (£)</span>
        <input type="number" step="0.01" min="0" value={menuPrice}
               onChange={(e) => setMenuPrice(e.target.value)} className={INPUT} />
      </label>
      <label className="text-sm">
        <span className="mb-1 block text-muted">Category</span>
        <select value={category} onChange={(e) => setCategory(e.target.value)} className={INPUT}>
          <option value="">Choose…</option>
          {CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
      </label>
      <label className="text-sm">
        <span className="mb-1 block text-muted">On the menu from</span>
        <input type="date" value={onMenuFrom} onChange={(e) => setOnMenuFrom(e.target.value)} className={INPUT} />
      </label>
      <label className="text-sm">
        <span className="mb-1 block text-muted">Until (blank if still on)</span>
        <input type="date" value={onMenuUntil} min={onMenuFrom} onChange={(e) => setOnMenuUntil(e.target.value)} className={INPUT} />
      </label>
      <div className="flex gap-2 sm:col-span-2 sm:pt-6">
        <button type="submit" disabled={submitting}
                className="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-accent-ink hover:opacity-90 disabled:opacity-50">
          {submitting ? 'Saving…' : submitLabel}
        </button>
        {onCancel && (
          <button type="button" onClick={onCancel}
                  className="rounded-lg border border-line px-4 py-2 text-sm hover:bg-bg">
            Cancel
          </button>
        )}
      </div>
      {error && <p className="text-sm text-danger sm:col-span-4">{error}</p>}
    </form>
  )
}

export default DishForm
