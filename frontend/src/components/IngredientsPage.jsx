import { percentMove, priceMove, usePriceChanges } from '../priceChanges'
import { useEffect, useState } from 'react'
import Card from './Card'
import PriceFields from './PriceFields'
import { getJson, postJson } from '../api'
import usePageImport from '../usePageImport'
import { emptyPrice, priceBody, priceProblem } from '../prices'
import { priceForDisplay, shortDate, sourceLabel } from '../format'

// Own prices (invoice, supplier list, manual) are highlighted; benchmarks are muted.
function SourceBadge({ source }) {
  return <span className={`chip ${source === 'benchmark' ? 'chip-muted' : 'chip-accent'}`}>{sourceLabel(source)}</span>
}

// Expanded row: record a new price, and the price history.
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
    <div className="grid gap-8 bg-bg px-5 py-5 lg:grid-cols-2">
      <div className="space-y-4">
        <h3 className="label">New price</h3>
        <PriceFields unit={ingredient.unit} price={price} onChange={setPrice} />
        {error && <p className="alert-error">{error}</p>}
        <button type="button" onClick={save} disabled={saving} className="btn btn-primary">
          {saving ? 'Saving…' : 'Save price'}
        </button>
      </div>
      <div className="space-y-4">
        <h3 className="label">History</h3>
        {!history ? (
          <p className="text-muted">Loading…</p>
        ) : (
          <ul className="card divide-y divide-line">
            {history.map((h, i) => (
              <li key={h.id} className="flex items-center justify-between gap-3 px-4 py-2.5">
                <div className="min-w-0 truncate">
                  <span className="num">{shortDate(h.effective_date)}</span>
                  {h.supplier && <span className="ml-2 text-muted">{h.supplier}</span>}
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  <span className={`num ${i === 0 ? 'font-semibold' : 'text-muted'}`}>
                    {priceForDisplay(h.price_per_unit, ingredient.unit)}
                  </span>
                  <SourceBadge source={h.source} />
                </div>
              </li>
            ))}
          </ul>
        )}
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
      <div className="space-y-4">
        <div className="grid gap-4 sm:grid-cols-3">
          <label className="field sm:col-span-2">
            <span className="label">Name</span>
            <input type="text" value={name} onChange={(e) => setName(e.target.value)} className="input" autoFocus />
          </label>
          <label className="field">
            <span className="label">Measured by</span>
            <select value={unit} onChange={(e) => changeUnit(e.target.value)} className="input">
              <option value="gram">Weight (g)</option>
              <option value="ml">Volume (ml)</option>
              <option value="each">Count (each)</option>
            </select>
          </label>
        </div>
        <PriceFields unit={unit} price={price} onChange={setPrice} />
        {error && <p className="alert-error">{error}</p>}
        <div className="flex justify-end gap-2">
          <button type="button" onClick={onCancel} className="btn btn-secondary">Cancel</button>
          <button type="button" onClick={save} disabled={saving} className="btn btn-primary">
            {saving ? 'Saving…' : 'Add ingredient'}
          </button>
        </div>
      </div>
    </Card>
  )
}

// ownCostShare: % of the menu's recipe cost on the restaurant's own prices (setup status).
function IngredientsPage({ onChanged, ownCostShare }) {
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
  const invoiceImport = usePageImport('invoice', 'Import invoices', reload, { multiple: true })
  // The latest price change per ingredient (latest month), for the chip beside its price.
  const priceChanges = usePriceChanges(null, loads)
  const changeById = {}
  for (const c of priceChanges ?? []) {
    if (!changeById[c.ingredient_id] || c.day > changeById[c.ingredient_id].day) changeById[c.ingredient_id] = c
  }

  if (invoiceImport.review) return invoiceImport.review
  if (error) return <p className="alert-error">{error}</p>
  if (!ingredients) return <p className="text-muted">Loading ingredients…</p>

  const inUse = ingredients.filter((i) => i.used_in > 0)
  const ownInUse = inUse.filter((i) => i.price_source !== 'benchmark').length

  const term = search.trim().toLowerCase()
  const shown = ingredients
    .filter((i) => i.name.toLowerCase().includes(term))
    .filter((i) => filter === 'all'
      || (filter === 'own' && i.price_source !== 'benchmark')
      || (filter === 'benchmark' && i.price_source === 'benchmark'))
    .sort((a, b) => a.name.localeCompare(b.name))

  return (
    <div className="space-y-5">
      <div className="tile tile-basil corner-bl flex-row flex-wrap items-center gap-x-12 gap-y-4 px-7 py-6">
        <div className="flex flex-col gap-2">
          <span className="tile-label">your own prices</span>
          <span className="figure text-[4.5rem]">
            {ownInUse}<span className="text-[2.25rem] opacity-80"> / {inUse.length}</span>
          </span>
        </div>
        <div className="flex min-w-[240px] flex-1 flex-col gap-2.5">
          <div className="h-3 overflow-hidden rounded-full bg-bg/25" role="img"
               aria-label={`${ownInUse} of ${inUse.length} ingredients in use have your own prices`}>
            <div className="h-full rounded-full bg-mustard" style={{ width: `${inUse.length ? (ownInUse / inUse.length) * 100 : 0}%` }} />
          </div>
          <span className="tile-label">ingredients in use · the rest on benchmark</span>
        </div>
        {ownCostShare != null && (
          <div className="flex flex-col gap-2">
            <span className="tile-label">of recipe cost</span>
            <span className="figure text-[4.5rem]">{Math.round(ownCostShare)}%</span>
          </div>
        )}
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-3">
          <input type="search" value={search} onChange={(e) => setSearch(e.target.value)}
                 placeholder="Search ingredients" className="input w-56" aria-label="Search ingredients" />
          <div className="segmented" role="group" aria-label="Filter by price source">
            {[['all', 'All'], ['own', 'Your prices'], ['benchmark', 'Benchmark only']].map(([value, label]) => (
              <button key={value} type="button" aria-pressed={filter === value} onClick={() => setFilter(value)}>{label}</button>
            ))}
          </div>
        </div>
        <div className="flex gap-2">
          {invoiceImport.button}
          {!adding && <button type="button" onClick={() => setAdding(true)} className="btn btn-primary">+ Add ingredient</button>}
        </div>
      </div>
      {invoiceImport.error && <p className="alert-error">{invoiceImport.error}</p>}

      {adding && <AddIngredient onAdded={() => { setAdding(false); reload() }} onCancel={() => setAdding(false)} />}

      <Card flush>
        <div className="overflow-x-auto">
          <table className="table min-w-[600px] table-fixed">
            <colgroup>
              <col />
              <col className="w-32" />
              <col className="w-48" />
              <col className="w-28" />
              <col className="w-12" />
            </colgroup>
            <thead>
              <tr>
                <th>Ingredient</th>
                <th className="text-right">Price</th>
                <th>Source</th>
                <th className="text-right">Used in</th>
                <th><span className="sr-only">Expand</span></th>
              </tr>
            </thead>
            <tbody>
              {shown.length === 0 && (
                <tr><td colSpan={5} className="py-8 text-center text-muted">No ingredients match.</td></tr>
              )}
              {shown.map((ing) => {
                const open = openId === ing.id
                return [
                  <tr key={ing.id} onClick={() => setOpenId(open ? null : ing.id)} className="row-link" aria-expanded={open}>
                    <td className="truncate font-semibold">{ing.name}</td>
                    <td className="num whitespace-nowrap text-right">
                      {changeById[ing.id] && (
                        <span title={`${priceMove(changeById[ing.id])} from ${shortDate(changeById[ing.id].day)}`}
                              className={`chip mr-2 ${changeById[ing.id].is_alert ? 'chip-accent' : 'chip-muted'}`}>
                          {changeById[ing.id].change_percent > 0 ? '▲' : '▼'} {percentMove(changeById[ing.id]).slice(1)}
                        </span>
                      )}
                      {ing.price_per_unit != null ? priceForDisplay(ing.price_per_unit, ing.unit) : '—'}
                    </td>
                    <td>
                      {ing.price_source && (
                        <div className="flex items-center gap-2">
                          <SourceBadge source={ing.price_source} />
                          <span className="num whitespace-nowrap text-sm text-muted">{shortDate(ing.price_date)}</span>
                        </div>
                      )}
                    </td>
                    <td className="num text-right text-muted">
                      {ing.used_in ? `${ing.used_in} dish${ing.used_in === 1 ? '' : 'es'}` : '—'}
                    </td>
                    <td className="text-right text-muted">{open ? '▴' : '▾'}</td>
                  </tr>,
                  open && (
                    <tr key={`${ing.id}-detail`}>
                      <td colSpan={5} className="!p-0">
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
