import { useEffect, useState } from 'react'
import Card from './Card'
import PriceFields from './PriceFields'
import { getJson, postJson } from '../api'
import { emptyPrice, priceBody, priceProblem } from '../prices'
import { priceForDisplay, shortDate, sourceLabel } from '../format'

const INPUT = 'w-full rounded-lg border border-line bg-surface px-3 py-2 text-ink focus:border-accent focus:outline-none'
const PRIMARY = 'rounded-lg bg-accent px-4 py-2 text-sm font-medium text-accent-ink hover:opacity-90 disabled:opacity-50'
const SECONDARY = 'rounded-lg border border-line bg-surface px-4 py-2 text-sm hover:bg-bg'

function SourceBadge({ source }) {
  const own = source !== 'benchmark'
  return (
    <span className={`whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-medium ${
      own ? 'bg-accent/10 text-accent' : 'bg-line/60 text-muted'
    }`}>
      {sourceLabel(source)}
    </span>
  )
}

// Expanded row: price history, and a form to record a new price.
function IngredientDetail({ ingredient, onPriceAdded }) {
  const [history, setHistory] = useState(null)
  const [price, setPrice] = useState(() => emptyPrice(ingredient.unit))
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)
  const [loads, setLoads] = useState(0)

  useEffect(() => {
    let ignore = false
    getJson(`/ingredients/${ingredient.id}/prices`)
      .then((rows) => { if (!ignore) setHistory(rows) })
      .catch((err) => { if (!ignore) setError(err.message) })
    return () => { ignore = true }
  }, [ingredient.id, loads])

  const save = () => {
    const problem = priceProblem(price)
    if (problem) return setError(problem)
    setSaving(true)
    setError(null)
    postJson(`/ingredients/${ingredient.id}/prices`, priceBody(price))
      .then(() => {
        setPrice(emptyPrice(ingredient.unit))
        setLoads((n) => n + 1)
        onPriceAdded()
      })
      .catch((err) => setError(err.message))
      .finally(() => setSaving(false))
  }

  return (
    <div className="grid gap-6 bg-bg/60 px-5 py-4 lg:grid-cols-2">
      <div>
        <p className="mb-2 text-sm font-medium">Record a new price</p>
        <PriceFields unit={ingredient.unit} price={price} onChange={setPrice} />
        {error && <p className="mt-2 text-sm text-danger">{error}</p>}
        <button type="button" onClick={save} disabled={saving} className={`${PRIMARY} mt-3`}>
          {saving ? 'Saving…' : 'Save price'}
        </button>
      </div>
      <div>
        <p className="mb-2 text-sm font-medium">Price history</p>
        {!history ? (
          <p className="text-sm text-muted">Loading…</p>
        ) : (
          <ul className="divide-y divide-line rounded-lg border border-line bg-surface text-sm">
            {history.map((h, i) => (
              <li key={h.id} className="flex items-center justify-between gap-3 px-3 py-2">
                <div>
                  <span className="tabular-nums">{shortDate(h.effective_date)}</span>
                  <span className="ml-2 text-muted">{h.supplier ?? ''}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`tabular-nums ${i === 0 ? 'font-medium' : 'text-muted'}`}>
                    {priceForDisplay(h.price_per_unit, ingredient.unit)}
                  </span>
                  <SourceBadge source={h.source} />
                </div>
              </li>
            ))}
          </ul>
        )}
        <p className="mt-2 text-xs text-muted">
          Costing uses your most recent own price. Benchmarks are only used until you have one.
        </p>
      </div>
    </div>
  )
}

function AddIngredient({ onAdded, onCancel }) {
  const [name, setName] = useState('')
  const [unit, setUnit] = useState('gram')
  const [price, setPrice] = useState(() => emptyPrice('gram'))
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)

  const changeUnit = (u) => {
    setUnit(u)
    setPrice(emptyPrice(u))
  }

  const save = () => {
    if (name.trim() === '') return setError('Enter a name.')
    const problem = priceProblem(price)
    if (problem) return setError(problem)
    setSaving(true)
    setError(null)
    postJson('/ingredients', { name: name.trim(), unit, ...priceBody(price) })
      .then(onAdded)
      .catch((err) => {
        setError(err.message)
        setSaving(false)
      })
  }

  return (
    <Card title="New ingredient">
      <div className="grid gap-3 sm:grid-cols-[2fr_1fr]">
        <label className="text-sm">
          <span className="mb-1 block text-muted">Name</span>
          <input type="text" value={name} onChange={(e) => setName(e.target.value)} className={INPUT} autoFocus />
        </label>
        <label className="text-sm">
          <span className="mb-1 block text-muted">Measured by</span>
          <select value={unit} onChange={(e) => changeUnit(e.target.value)} className={INPUT}>
            <option value="gram">Weight (g)</option>
            <option value="ml">Volume (ml)</option>
            <option value="each">Count (each)</option>
          </select>
        </label>
      </div>
      <div className="mt-3">
        <PriceFields unit={unit} price={price} onChange={setPrice} />
      </div>
      {error && <p className="mt-2 text-sm text-danger">{error}</p>}
      <div className="mt-4 flex gap-2">
        <button type="button" onClick={save} disabled={saving} className={PRIMARY}>
          {saving ? 'Saving…' : 'Add ingredient'}
        </button>
        <button type="button" onClick={onCancel} className={SECONDARY}>Cancel</button>
      </div>
    </Card>
  )
}

function IngredientsPage({ onChanged }) {
  const [ingredients, setIngredients] = useState(null)
  const [error, setError] = useState(null)
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState('all')
  const [openId, setOpenId] = useState(null)
  const [adding, setAdding] = useState(false)
  const [loads, setLoads] = useState(0)

  useEffect(() => {
    let ignore = false
    getJson('/ingredients')
      .then((rows) => { if (!ignore) setIngredients(rows) })
      .catch((err) => { if (!ignore) setError(err.message) })
    return () => { ignore = true }
  }, [loads])

  const reload = () => {
    setLoads((n) => n + 1)
    onChanged()  // prices change dish costs, so the dashboard needs refreshing too
  }

  if (error) return <p className="rounded-xl border border-danger/40 bg-surface p-5 text-danger">{error}</p>
  if (!ingredients) return <p className="text-muted">Loading ingredients…</p>

  const ownCount = ingredients.filter((i) => i.price_source && i.price_source !== 'benchmark').length
  const inUse = ingredients.filter((i) => i.used_in > 0)
  const ownInUse = inUse.filter((i) => i.price_source !== 'benchmark').length

  const term = search.trim().toLowerCase()
  const shown = ingredients
    .filter((i) => i.name.toLowerCase().includes(term))
    .filter((i) => filter === 'all'
      || (filter === 'own' && i.price_source !== 'benchmark')
      || (filter === 'benchmark' && i.price_source === 'benchmark'))
    .sort((a, b) => a.name.localeCompare(b.name))

  const tab = (value, label) => (
    <button type="button" onClick={() => setFilter(value)}
            className={`rounded-lg px-3 py-1.5 text-sm ${filter === value ? 'bg-surface font-medium shadow-sm' : 'text-muted hover:text-ink'}`}>
      {label}
    </button>
  )

  return (
    <div className="space-y-5">
      <div className="rounded-xl border border-line bg-surface p-4 shadow-sm">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <p className="text-sm">
            <span className="text-lg font-semibold tabular-nums">{ownInUse} of {inUse.length}</span>
            <span className="text-muted"> ingredients on your menu use your own prices</span>
          </p>
          <p className="text-sm text-muted">{ownCount} own prices · {ingredients.length} ingredients in total</p>
        </div>
        <div className="mt-3 h-2 overflow-hidden rounded-full bg-bg">
          <div className="h-full rounded-full bg-accent" style={{ width: `${inUse.length ? (ownInUse / inUse.length) * 100 : 0}%` }} />
        </div>
        <p className="mt-2 text-xs text-muted">The rest are costed on benchmark estimates. Add prices from your invoices to make margins more accurate.</p>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-3">
          <input type="search" value={search} onChange={(e) => setSearch(e.target.value)}
                 placeholder="Search ingredients" className={`${INPUT} w-56`} />
          <div className="flex gap-1 rounded-xl bg-line/50 p-1">
            {tab('all', 'All')}
            {tab('own', 'Your prices')}
            {tab('benchmark', 'Benchmark only')}
          </div>
        </div>
        {!adding && (
          <button type="button" onClick={() => setAdding(true)} className={PRIMARY}>+ Add ingredient</button>
        )}
      </div>

      {adding && <AddIngredient onAdded={() => { setAdding(false); reload() }} onCancel={() => setAdding(false)} />}

      <Card flush>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[560px] table-fixed text-sm">
            <colgroup>
              <col />
              <col className="w-32" />
              <col className="w-40" />
              <col className="w-24" />
              <col className="w-10" />
            </colgroup>
            <thead>
              <tr className="border-b border-line text-xs uppercase tracking-wide text-muted">
                <th className="py-2 pl-5 pr-3 text-left font-medium">Ingredient</th>
                <th className="px-3 py-2 text-right font-medium">Price</th>
                <th className="px-3 py-2 text-left font-medium">Source</th>
                <th className="px-3 py-2 text-right font-medium">Used in</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {shown.length === 0 && (
                <tr><td colSpan={5} className="px-5 py-6 text-center text-muted">No ingredients match.</td></tr>
              )}
              {shown.map((ing) => {
                const open = openId === ing.id
                return [
                  <tr key={ing.id} onClick={() => setOpenId(open ? null : ing.id)}
                      className={`cursor-pointer border-b border-line hover:bg-bg ${open ? 'bg-bg' : ''}`}
                      aria-expanded={open}>
                    <td className="truncate py-3 pl-5 pr-3 font-medium">{ing.name}</td>
                    <td className="whitespace-nowrap px-3 py-3 text-right tabular-nums">
                      {ing.price_per_unit != null ? priceForDisplay(ing.price_per_unit, ing.unit) : '—'}
                    </td>
                    <td className="px-3 py-3">
                      {ing.price_source && (
                        <div className="flex items-center gap-2">
                          <SourceBadge source={ing.price_source} />
                          <span className="whitespace-nowrap text-xs text-muted">{shortDate(ing.price_date)}</span>
                        </div>
                      )}
                    </td>
                    <td className="px-3 py-3 text-right tabular-nums text-muted">
                      {ing.used_in ? `${ing.used_in} dish${ing.used_in === 1 ? '' : 'es'}` : '—'}
                    </td>
                    <td className="pr-5 text-right text-muted">{open ? '▴' : '▾'}</td>
                  </tr>,
                  open && (
                    <tr key={`${ing.id}-detail`} className="border-b border-line">
                      <td colSpan={5} className="p-0">
                        <IngredientDetail ingredient={ing} onPriceAdded={reload} />
                      </td>
                    </tr>
                  ),
                ]
              })}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  )
}

export default IngredientsPage
