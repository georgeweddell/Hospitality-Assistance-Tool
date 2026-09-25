import { useEffect, useState } from 'react'
import Card from './Card'
import RecipeEditor from './RecipeEditor'
import { getJson, postJson } from '../api'
import { pounds } from '../format'

// Setup step 2: recipes for the dishes still without one, one at a time, in
// menu order (queue = setup status's needs_recipe). Saving refreshes the
// status, which moves the queue on. Once the owner has used "Estimate with
// AI", the next dish's draft is fetched while they check the current one,
// so it's ready when they get there. It's still only a draft: nothing is
// saved until they press Save.
function RecipeStep({ queue, total, onChanged, onNext }) {
  const [skipped, setSkipped] = useState(() => new Set())
  const [ingredients, setIngredients] = useState(null)
  const [dish, setDish] = useState(null)
  const [aiUsed, setAiUsed] = useState(false)
  const [drafts, setDrafts] = useState({})   // dish id -> draft lines, or 'loading' / 'failed'
  const [error, setError] = useState(null)

  const pending = queue.filter((id) => !skipped.has(id))
  const current = pending[0] ?? null
  const next = pending[1] ?? null
  const afterNext = pending[2] ?? null

  useEffect(() => {
    getJson('/ingredients').then(setIngredients).catch((err) => setError(err.message))
  }, [])

  useEffect(() => {
    if (current === null) return
    let ignore = false
    getJson(`/dishes/${current}/detail`)
      .then((d) => { if (!ignore) setDish(d) })
      .catch((err) => { if (!ignore) setError(err.message) })
    return () => { ignore = true }
  }, [current])

  // Fetch a dish's AI draft in the background (once).
  const prepare = (id) => {
    if (id === null || drafts[id] !== undefined) return
    setDrafts((d) => ({ ...d, [id]: 'loading' }))
    postJson(`/dishes/${id}/estimate-recipe`, {})
      .then((lines) => setDrafts((d) => ({ ...d, [id]: lines })))
      .catch(() => setDrafts((d) => ({ ...d, [id]: 'failed' })))   // the owner can still press Estimate
  }

  // Moving on (saved or skipped): `next` becomes current, so make sure its draft
  // is coming and start the one after it, once the owner is using AI.
  const movingOn = (usingAi) => {
    if (!usingAi) return
    prepare(next)
    prepare(afterNext)
  }

  const done = total - queue.length

  if (current === null) {
    return (
      <Card title="Recipes" aside={<span className="count num">{done} / {total}</span>}>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <span className="flex flex-wrap gap-1.5">
            <span className="chip chip-accent num">{done} with a recipe</span>
            {skipped.size > 0 && <span className="chip chip-warn num">{skipped.size} skipped</span>}
          </span>
          <button type="button" onClick={onNext} className="btn btn-primary">Next: Sales</button>
        </div>
      </Card>
    )
  }

  const draft = drafts[current]
  const ready = ingredients && dish && dish.id === current && draft !== 'loading'

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="label num">Recipe {done + skipped.size + 1} of {total}</p>
          {dish && dish.id === current && (
            <>
              <h2 className="section-title mt-1">{dish.name}</h2>
              <p className="num mt-1 text-sm text-muted">
                {dish.category ?? 'No category'} · {pounds(dish.menu_price)}
                {dish.description && ` · ${dish.description}`}
              </p>
            </>
          )}
        </div>
        <button type="button" className="btn btn-secondary"
                onClick={() => { setSkipped((s) => new Set(s).add(current)); movingOn(aiUsed) }}>
          Skip for now
        </button>
      </div>

      {error && <p className="alert-error">{error}</p>}
      {ready ? (
        <RecipeEditor key={`${current}-${Array.isArray(draft) ? 'draft' : 'saved'}`}
                      dish={dish} ingredients={ingredients}
                      initialDraft={Array.isArray(draft) ? draft : null}
                      onEstimated={() => { setAiUsed(true); prepare(next) }}
                      onSaved={() => {
                        const usingAi = aiUsed || Array.isArray(draft)
                        setAiUsed(usingAi)
                        movingOn(usingAi)
                        onChanged()
                      }} />
      ) : (
        <div className="flex items-center gap-3 text-muted">
          <span className="h-4 w-4 animate-spin rounded-full border-2 border-line border-t-accent" aria-hidden="true" />
          {draft === 'loading' ? 'Preparing AI draft…' : 'Loading…'}
        </div>
      )}
    </div>
  )
}

export default RecipeStep
