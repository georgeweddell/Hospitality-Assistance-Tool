import { useState } from 'react'
import { CATEGORIES } from '../categories'

const today = () => new Date().toISOString().slice(0, 10)

// Name, price, category and menu dates. Used to add a dish and to edit one.
// Editing the price asks when the new price starts; the old one is kept for
// the days before, so past periods are analysed at what was charged.
function DishForm({ initial = {}, submitLabel, onSubmit, onCancel }) {
  const [name, setName] = useState(initial.name ?? '')
  const [menuPrice, setMenuPrice] = useState(initial.menu_price != null ? String(initial.menu_price) : '')
  const [category, setCategory] = useState(initial.category ?? '')
  const [onMenuFrom, setOnMenuFrom] = useState(initial.on_menu_from ?? today())
  const [priceFrom, setPriceFrom] = useState(today())
  const [onMenuUntil, setOnMenuUntil] = useState(initial.on_menu_until ?? '')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState(null)
  const priceChanged = initial.menu_price != null && Number(menuPrice) !== initial.menu_price

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
    if (priceChanged && !priceFrom) {
      setError('Enter when the new price starts.')
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
      ...(priceChanged && { price_from: priceFrom }),
    })
      .catch((err) => {
        setError(err.message)
        setSubmitting(false)
      })
  }

  return (
    <form onSubmit={handleSubmit} className="grid gap-4 sm:grid-cols-4">
      <label className="field sm:col-span-2">
        <span className="label">Dish name</span>
        <input type="text" value={name} onChange={(e) => setName(e.target.value)} className="input" autoFocus />
      </label>
      <label className="field">
        <span className="label">Menu price (£)</span>
        <input type="number" step="0.01" min="0" value={menuPrice}
               onChange={(e) => setMenuPrice(e.target.value)} className="input num" />
      </label>
      <label className="field">
        <span className="label">Category</span>
        <select value={category} onChange={(e) => setCategory(e.target.value)} className="input">
          <option value="">Choose…</option>
          {CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
      </label>
      <label className="field">
        <span className="label">On the menu from</span>
        <input type="date" value={onMenuFrom} onChange={(e) => setOnMenuFrom(e.target.value)} className="input" />
      </label>
      <label className="field">
        <span className="label">Until</span>
        <input type="date" value={onMenuUntil} min={onMenuFrom} onChange={(e) => setOnMenuUntil(e.target.value)}
               className="input" aria-describedby="until-hint" />
        <span id="until-hint" className="sr-only">Leave blank if the dish is still on the menu</span>
      </label>
      {priceChanged && (
        <label className="field">
          <span className="label">New price from</span>
          <input type="date" value={priceFrom} onChange={(e) => setPriceFrom(e.target.value)} className="input" />
        </label>
      )}
      <div className={`flex items-end justify-end gap-2 ${priceChanged ? '' : 'sm:col-span-2'}`}>
        {onCancel && <button type="button" onClick={onCancel} className="btn btn-secondary">Cancel</button>}
        <button type="submit" disabled={submitting} className="btn btn-primary">
          {submitting ? 'Saving…' : submitLabel}
        </button>
      </div>
      {error && <p className="alert-error sm:col-span-4">{error}</p>}
    </form>
  )
}

export default DishForm
