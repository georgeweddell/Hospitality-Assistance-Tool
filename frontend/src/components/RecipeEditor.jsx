import { useState } from 'react'
import Card from './Card'
import { postJson } from '../api'
import { percent, pounds, priceForDisplay, unitLabel } from '../format'

const INPUT = 'w-full rounded-lg border border-line bg-surface px-2.5 py-1.5 text-ink focus:border-accent focus:outline-none'

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
        <button
          type="button"
          onClick={estimate}
          disabled={estimating || saving}
          className="rounded-lg border border-line px-3 py-1.5 text-sm font-medium text-ink hover:bg-bg disabled:opacity-50"
        >
          {estimating ? 'Estimating…' : '✦ Estimate with AI'}
        </button>
      }
      flush
    >
      {isDraft && (
        <p className="mx-5 mb-3 rounded-lg bg-accent/10 px-3 py-2 text-sm text-ink">
          <span className="font-medium">AI draft.</span> Check each line against how you actually make it, then save. Nothing is saved yet.
        </p>
      )}
      {error && <p className="mx-5 mb-3 rounded-lg border border-danger/40 px-3 py-2 text-sm text-danger">{error}</p>}

      {rows.length === 0 ? (
        <div className="mx-5 mb-4 rounded-lg border border-dashed border-line p-6 text-center text-sm text-muted">
          No recipe yet. Add ingredients one by one, or let AI draft it for you to check.
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-line text-left text-xs uppercase tracking-wide text-muted">
                <th className="py-2 pl-5 pr-2 font-medium">Ingredient</th>
                <th className="w-36 px-2 py-2 font-medium">Quantity</th>
                <th className="px-2 py-2 text-right font-medium">Price</th>
                <th className="px-2 py-2 text-right font-medium">Cost</th>
                <th className="w-10 py-2 pr-5" />
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => {
                const ing = byId[row.ingredientId]
                const unitClash = row.draft && ing && row.draft.unit !== ing.unit
                const cost = lineCost(row)
                return (
                  <tr key={row.key} className="border-b border-line align-top last:border-0">
                    <td className="py-2.5 pl-5 pr-2">
                      <select
                        value={row.ingredientId}
                        onChange={(e) => updateRow(row.key, { ingredientId: e.target.value === '' ? '' : Number(e.target.value) })}
                        className={`${INPUT} ${row.ingredientId === '' && showProblems ? 'border-danger' : ''}`}
                        aria-label="Ingredient"
                      >
                        <option value="">Choose an ingredient…</option>
                        {sortedIngredients.map((i) => <option key={i.id} value={i.id}>{i.name}</option>)}
                      </select>

                      {row.draft && row.ingredientId === '' && (
                        <div className="mt-1.5 text-xs">
                          <p className="text-warn">AI suggested “{row.draft.name}”, which isn't in your ingredient list.</p>
                          <div className="mt-1 flex flex-wrap items-center gap-1.5">
                            {row.draft.suggestions.map((s) => (
                              <button key={s.id} type="button" onClick={() => updateRow(row.key, { ingredientId: s.id })}
                                      className="rounded-full border border-line px-2 py-0.5 hover:border-accent hover:text-accent">
                                {s.name}
                              </button>
                            ))}
                            <button type="button" onClick={() => leaveOut(row)} className="px-1 text-muted underline hover:text-ink">
                              Leave out (not costed)
                            </button>
                          </div>
                        </div>
                      )}
                      {unitClash && (
                        <p className="mt-1.5 text-xs text-warn">
                          AI gave this in {unitLabel(row.draft.unit)}, but {ing.name} is priced per {unitLabel(ing.unit)}. Check the quantity.
                        </p>
                      )}
                    </td>
                    <td className="px-2 py-2.5">
                      <div className="flex items-center gap-1.5">
                        <input
                          type="number"
                          min="0"
                          step="any"
                          value={row.quantity}
                          onChange={(e) => updateRow(row.key, { quantity: e.target.value })}
                          className={`${INPUT} text-right tabular-nums`}
                          aria-label="Quantity"
                        />
                        <span className="w-8 text-xs text-muted">{ing ? unitLabel(ing.unit) : ''}</span>
                      </div>
                    </td>
                    <td className="whitespace-nowrap px-2 py-2.5 pt-4 text-right text-xs text-muted">
                      {ing?.price_per_unit != null && (
                        <>
                          {priceForDisplay(ing.price_per_unit, ing.unit)}
                          <div>{ing.price_source === 'benchmark' ? 'benchmark' : ing.price_source?.replace('_', ' ')}</div>
                        </>
                      )}
                    </td>
                    <td className="whitespace-nowrap px-2 py-2.5 pt-4 text-right tabular-nums">
                      {cost != null ? pounds(cost) : '—'}
                    </td>
                    <td className="py-2.5 pr-5 pt-3.5 text-right">
                      <button type="button" onClick={() => removeRow(row.key)} aria-label="Remove line"
                              className="rounded px-1.5 text-lg leading-none text-muted hover:text-danger">
                        ×
                      </button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-line px-5 py-3">
        <button type="button" onClick={addRow} className="text-sm font-medium text-accent hover:underline">
          + Add ingredient
        </button>
        <p className="text-sm text-muted">
          Plate cost <span className="font-semibold tabular-nums text-ink">{pounds(previewCost)}</span>
          <span className="mx-2">·</span>
          Margin <span className="font-semibold tabular-nums text-ink">{pounds(previewMargin)}</span>
          {' '}({percent((previewMargin / dish.menu_price) * 100)})
        </p>
      </div>

      {skipped.length > 0 && (
        <div className="border-t border-line px-5 py-3 text-sm">
          <span className="text-warn">Not costed:</span>{' '}
          {skipped.map((name) => (
            <span key={name} className="ml-1.5 inline-flex items-center gap-1 rounded-full bg-warn-bg px-2 py-0.5 text-xs text-warn">
              {name}
              <button type="button" aria-label={`Remove ${name}`} onClick={() => { setSkipped((s) => s.filter((n) => n !== name)); setDirty(true) }}
                      className="hover:text-ink">×</button>
            </span>
          ))}
        </div>
      )}

      {showProblems && problems.length > 0 && (
        <ul className="mx-5 mb-3 list-disc space-y-0.5 rounded-lg border border-danger/40 py-2 pl-8 pr-3 text-sm text-danger">
          {problems.map((p) => <li key={p}>{p}</li>)}
        </ul>
      )}

      {dirty && (
        <div className="flex justify-end gap-2 border-t border-line bg-bg/60 px-5 py-3">
          <button type="button" onClick={reset} disabled={saving}
                  className="rounded-lg border border-line bg-surface px-4 py-2 text-sm hover:bg-bg">
            Discard changes
          </button>
          <button type="button" onClick={save} disabled={saving}
                  className="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-accent-ink hover:opacity-90 disabled:opacity-50">
            {saving ? 'Saving…' : 'Save recipe'}
          </button>
        </div>
      )}
    </Card>
  )
}

export default RecipeEditor
