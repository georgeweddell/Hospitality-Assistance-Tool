import { useState } from 'react'
import Card from './Card'
import { postJson } from '../api'
import { percent, pounds, priceForDisplay, sourceLabel, unitLabel } from '../format'

let nextKey = 1
const newKey = () => nextKey++

// A saved recipe line -> an editor row.
function rowFromLine(line) {
  return { key: newKey(), ingredientId: line.ingredient_id, quantity: String(line.quantity), draft: null }
}

// An AI draft line -> an editor row. `draft` keeps what Claude said, so the
// row can show its suggestions and warn about units until someone checks it.
function rowFromDraft(item) {
  return {
    key: newKey(),
    ingredientId: item.matched_ingredient_id ?? '',
    quantity: String(item.quantity),
    draft: { name: item.name, unit: item.unit, suggestions: item.suggestions },
  }
}

// Problems that block saving, worked out from the rows.
function findProblems(rows, byId) {
  const problems = []
  const unresolved = rows.filter((r) => r.ingredientId === '').length
  if (unresolved) {
    problems.push(`${unresolved} line${unresolved === 1 ? '' : 's'} still need${unresolved === 1 ? 's' : ''} an ingredient. Pick one, or leave it out.`)
  }
  if (rows.some((r) => !(Number(r.quantity) > 0))) problems.push('Every quantity must be more than 0.')
  const seen = new Set()
  for (const r of rows) {
    if (r.ingredientId === '') continue
    if (seen.has(r.ingredientId)) problems.push(`${byId[r.ingredientId].name} appears twice. Combine it into one line.`)
    seen.add(r.ingredientId)
  }
  return problems
}

function RecipeEditor({ dish, ingredients, onSaved }) {
  const byId = Object.fromEntries(ingredients.map((i) => [i.id, i]))
  const sortedIngredients = [...ingredients].sort((a, b) => a.name.localeCompare(b.name))

  const [rows, setRows] = useState(() => dish.lines.map(rowFromLine))
  const [skipped, setSkipped] = useState(dish.skipped_ingredients)
  const [dirty, setDirty] = useState(false)
  const [isDraft, setIsDraft] = useState(false)
  const [estimating, setEstimating] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)
  const [showProblems, setShowProblems] = useState(false)

  const change = (updater) => {
    setRows(updater)
    setDirty(true)
  }
  const updateRow = (key, fields) => change((rs) => rs.map((r) => (r.key === key ? { ...r, ...fields } : r)))
  const removeRow = (key) => change((rs) => rs.filter((r) => r.key !== key))
  const addRow = () => change((rs) => [...rs, { key: newKey(), ingredientId: '', quantity: '', draft: null }])

  // Leaving an AI line out records it as "not costed" on the dish.
  const leaveOut = (row) => {
    removeRow(row.key)
    setSkipped((s) => (s.includes(row.draft.name) ? s : [...s, row.draft.name]))
  }

  const reset = () => {
    setRows(dish.lines.map(rowFromLine))
    setSkipped(dish.skipped_ingredients)
    setDirty(false)
    setIsDraft(false)
    setError(null)
    setShowProblems(false)
  }

  const estimate = () => {
    if (rows.length > 0 && !window.confirm('Replace the lines below with a new AI estimate? Nothing is saved until you press Save.')) return
    setEstimating(true)
    setError(null)
    postJson(`/dishes/${dish.id}/estimate-recipe`, {})
      .then((draft) => {
        setRows(draft.map(rowFromDraft))
        setSkipped([])
        setDirty(true)
        setIsDraft(true)
        setShowProblems(false)
      })
      .catch((err) => setError(err.message))
      .finally(() => setEstimating(false))
  }

  const problems = findProblems(rows, byId)

  const save = () => {
    if (problems.length) {
      setShowProblems(true)
      return
    }
    setSaving(true)
    setError(null)
    postJson(`/dishes/${dish.id}/recipe`, {
      ingredients: rows.map((r) => ({ ingredient_id: Number(r.ingredientId), quantity: Number(r.quantity) })),
      skipped_ingredients: skipped,
    })
      .then(() => onSaved())
      .catch((err) => {
        setError(err.message)
        setSaving(false)
      })
  }

  // Live preview while editing. The saved figures come from the backend's costing engine.
  const lineCost = (r) => {
    const ing = byId[r.ingredientId]
    return ing?.price_per_unit != null && Number(r.quantity) > 0 ? Number(r.quantity) * ing.price_per_unit : null
  }
  const previewCost = rows.reduce((sum, r) => sum + (lineCost(r) ?? 0), 0)
  const previewMargin = dish.menu_price - previewCost

  return (
    <Card
      title="Recipe"
      aside={
        <button type="button" onClick={estimate} disabled={estimating || saving} className="btn btn-secondary btn-sm">
          {estimating ? 'Estimating…' : '✦ Estimate with AI'}
        </button>
      }
      flush
    >
      {isDraft && (
        <p className="alert-info mx-5 mb-4">
          <span className="font-semibold">AI draft.</span> Check each line, then save.
        </p>
      )}
      {error && <p className="alert-error mx-5 mb-4">{error}</p>}

      {rows.length === 0 ? (
        <div className="empty mx-5 mb-5">No recipe yet. Add ingredients, or let AI draft one for you to check.</div>
      ) : (
        <div className="overflow-x-auto">
          <table className="table min-w-[640px]">
            <thead>
              <tr>
                <th>Ingredient</th>
                <th className="w-40">Quantity</th>
                <th className="w-32 text-right">Price</th>
                <th className="w-24 text-right">Cost</th>
                <th className="w-12"><span className="sr-only">Remove</span></th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => {
                const ing = byId[row.ingredientId]
                const unitClash = row.draft && ing && row.draft.unit !== ing.unit
                const cost = lineCost(row)
                return (
                  <tr key={row.key} className="align-top">
                    <td>
                      <select
                        value={row.ingredientId}
                        onChange={(e) => updateRow(row.key, { ingredientId: e.target.value === '' ? '' : Number(e.target.value) })}
                        className={`input py-1.5 ${row.ingredientId === '' && showProblems ? 'input-invalid' : ''}`}
                        aria-label="Ingredient"
                      >
                        <option value="">Choose an ingredient…</option>
                        {sortedIngredients.map((i) => <option key={i.id} value={i.id}>{i.name}</option>)}
                      </select>

                      {row.draft && row.ingredientId === '' && (
                        <div className="mt-2 flex flex-wrap items-center gap-1.5 text-sm">
                          <span className="chip chip-warn">“{row.draft.name}” not in your list</span>
                          {row.draft.suggestions.map((s) => (
                            <button key={s.id} type="button" onClick={() => updateRow(row.key, { ingredientId: s.id })}
                                    className="btn btn-secondary btn-sm">
                              {s.name}
                            </button>
                          ))}
                          <button type="button" onClick={() => leaveOut(row)} className="link text-sm">Leave out</button>
                        </div>
                      )}
                      {unitClash && (
                        <p className="mt-2 text-sm text-warn">
                          AI gave {unitLabel(row.draft.unit)}; {ing.name} is priced per {unitLabel(ing.unit)}. Check the quantity.
                        </p>
                      )}
                    </td>
                    <td>
                      <div className="flex items-center gap-2">
                        <input
                          type="number"
                          min="0"
                          step="any"
                          value={row.quantity}
                          onChange={(e) => updateRow(row.key, { quantity: e.target.value })}
                          className="input num py-1.5 text-right"
                          aria-label="Quantity"
                        />
                        <span className="w-9 text-sm text-muted">{ing ? unitLabel(ing.unit) : ''}</span>
                      </div>
                    </td>
                    <td className="num whitespace-nowrap pt-3.5 text-right text-sm">
                      {ing?.price_per_unit != null && (
                        <>
                          {priceForDisplay(ing.price_per_unit, ing.unit)}
                          <div className="text-xs text-muted">{sourceLabel(ing.price_source)}</div>
                        </>
                      )}
                    </td>
                    <td className="num whitespace-nowrap pt-3.5 text-right font-semibold">
                      {cost != null ? pounds(cost) : '—'}
                    </td>
                    <td className="pt-3 text-right">
                      <button type="button" onClick={() => removeRow(row.key)} aria-label="Remove line" className="btn-icon">×</button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-line px-5 py-3.5">
        <button type="button" onClick={addRow} className="link">+ Add ingredient</button>
        <p className="num text-muted">
          Plate cost <span className="font-display text-base font-semibold text-ink">{pounds(previewCost)}</span>
          <span className="mx-2">·</span>
          Margin <span className="font-display text-base font-semibold text-ink">{pounds(previewMargin)}</span>
          {' '}({percent((previewMargin / dish.menu_price) * 100)})
        </p>
      </div>

      {skipped.length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5 border-t border-line px-5 py-3 text-sm">
          <span className="label">Not costed</span>
          {skipped.map((name) => (
            <span key={name} className="chip chip-warn">
              {name}
              <button type="button" aria-label={`Remove ${name}`} className="hover:text-ink"
                      onClick={() => { setSkipped((s) => s.filter((n) => n !== name)); setDirty(true) }}>×</button>
            </span>
          ))}
        </div>
      )}

      {showProblems && problems.length > 0 && (
        <ul className="alert-error mx-5 mb-4 list-disc space-y-0.5 pl-8">
          {problems.map((p) => <li key={p}>{p}</li>)}
        </ul>
      )}

      {dirty && (
        <div className="flex justify-end gap-2 border-t border-line bg-bg px-5 py-3.5">
          <button type="button" onClick={reset} disabled={saving} className="btn btn-secondary">Discard changes</button>
          <button type="button" onClick={save} disabled={saving} className="btn btn-primary">
            {saving ? 'Saving…' : 'Save recipe'}
          </button>
        </div>
      )}
    </Card>
  )
}

export default RecipeEditor
