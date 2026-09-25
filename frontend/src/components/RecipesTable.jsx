import { useEffect, useRef, useState } from 'react'
import Card from './Card'
import ConfirmDialog from './ConfirmDialog'
import Hint from './Hint'
import RecipeEditor from './RecipeEditor'
import { getJson, postJson } from '../api'
import { CATEGORIES } from '../categories'
import { percent, pounds } from '../format'

// Every dish on the menu with its recipe: estimate one or all with AI, open one
// to edit, or confirm an AI estimate ("Looks right"). Used on the Setup page and
// the Menu page's Recipes tab.
//
// "Estimate all" saves each recipe straight away as an unchecked AI estimate
// (agreed with George): it still counts in the analysis, and its checks are
// shown here until the owner saves it in the editor or presses Looks right.

const PARALLEL = 3   // estimates running at once

const STATUS = {
  none: ['chip-warn', 'No recipe'],
  ai_unchecked: ['chip-accent', 'AI · unchecked'],
  checked: ['chip-muted', 'Checked'],
}

// Short label and the explanation on hover, for each check (recipe_checks.py).
function checkChip(check, row) {
  const food = row.food_cost_percent != null ? `Food cost ${percent(row.food_cost_percent, 0)}` : 'Food cost'
  return {
    food_cost_high: [food, 'Over 40% of the menu price. Check the quantities and prices.'],
    food_cost_low: [food, 'Under 8% of the menu price. Check nothing is missing.'],
    big_line: ['Large portion', 'A line over 500 g, 500 ml or 12 each for one portion.'],
    few_ingredients: ['1 ingredient', 'Fewer than 2 ingredients.'],
    left_out: ['Not costed', "Claude named ingredients that aren't in your list, so they're left out of the cost. Open the recipe to add them."],
    unit: ['Check unit', "A line was given in a different unit from its ingredient (e.g. grams of egg), so its quantity may be wrong."],
  }[check]
}

const byMenuOrder = (a, b) =>
  (CATEGORIES.indexOf(a.category) + 1 || 99) - (CATEGORIES.indexOf(b.category) + 1 || 99) || a.name.localeCompare(b.name)

// A small icon button; its label shows as the browser's tooltip.
// A small text button for a row's actions (words, not glyphs).
function RowButton({ label, onClick, disabled, children }) {
  return (
    <button type="button" onClick={onClick} disabled={disabled} aria-label={label} title={label}
            className="btn btn-secondary btn-sm ml-1.5">
      {children}
    </button>
  )
}

function RecipesTable({ onChanged }) {
  const [rows, setRows] = useState(null)
  const [ingredients, setIngredients] = useState(null)
  const [filter, setFilter] = useState('all')
  const [open, setOpen] = useState(null)          // { id, dish } being edited inline
  const [asking, setAsking] = useState(null)      // confirm: { ids, name?, replaces }
  const [running, setRunning] = useState(null)    // { total, done, failed } while estimating
  const [busy, setBusy] = useState(() => new Set())   // dish ids being estimated
  const [errors, setErrors] = useState({})        // dish id -> message
  const [error, setError] = useState(null)
  const stop = useRef(false)

  const load = () => getJson('/recipes').then((r) => setRows(r.sort(byMenuOrder))).catch((err) => setError(err.message))

  useEffect(() => {
    let ignore = false
    Promise.all([getJson('/recipes'), getJson('/ingredients')])
      .then(([r, ings]) => {
        if (ignore) return
        setRows(r.sort(byMenuOrder))
        setIngredients(ings)
      })
      .catch((err) => { if (!ignore) setError(err.message) })
    return () => { ignore = true }
  }, [])

  const replaceRow = (row) => setRows((rs) => rs.map((r) => (r.dish_id === row.dish_id ? row : r)))
  const setBusyFor = (id, on) => setBusy((b) => {
    const next = new Set(b)
    if (on) next.add(id)
    else next.delete(id)
    return next
  })

  // Estimate and save each dish, PARALLEL at a time, until done or stopped.
  const estimate = (ids) => {
    setAsking(null)
    setOpen(null)
    stop.current = false
    setRunning({ total: ids.length, done: 0, failed: 0 })
    const queue = [...ids]
    const worker = () => {
      if (stop.current || queue.length === 0) return Promise.resolve()
      const id = queue.shift()
      setBusyFor(id, true)
      return postJson(`/dishes/${id}/estimate-and-save`, {})
        .then((row) => {
          replaceRow(row)
          setErrors((e) => ({ ...e, [id]: undefined }))
          setRunning((r) => ({ ...r, done: r.done + 1 }))
        })
        .catch((err) => {
          setErrors((e) => ({ ...e, [id]: err.message }))
          setRunning((r) => ({ ...r, done: r.done + 1, failed: r.failed + 1 }))
        })
        .finally(() => setBusyFor(id, false))
        .then(worker)
    }
    Promise.all(Array.from({ length: Math.min(PARALLEL, ids.length) }, worker)).then(() => {
      setRunning(null)
      onChanged()
    })
  }

  const looksRight = (id) => {
    setBusyFor(id, true)
    postJson(`/dishes/${id}/recipe/checked`, {})
      .then((row) => {
        replaceRow(row)
        onChanged()
      })
      .catch((err) => setError(err.message))
      .finally(() => setBusyFor(id, false))
  }

  const edit = (id) => {
    if (open?.id === id) return setOpen(null)
    setOpen({ id, dish: null })
    getJson(`/dishes/${id}/detail`)
      .then((dish) => setOpen((o) => (o?.id === id ? { id, dish } : o)))
      .catch((err) => setError(err.message))
  }

  const saved = () => {
    setOpen(null)
    load()
    onChanged()
  }

  if (error && !rows) return <p className="alert-error">{error}</p>
  if (!rows || !ingredients) return <p className="text-muted">Loading recipes…</p>

  const counts = { none: 0, ai_unchecked: 0, checked: 0 }
  for (const r of rows) counts[r.status] += 1
  const missing = rows.filter((r) => r.status === 'none').map((r) => r.dish_id)
  const shown = rows.filter((r) => filter === 'all' || r.status === filter)

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="segmented" role="group" aria-label="Show">
          {[['all', 'All', rows.length], ['none', 'No recipe', counts.none],
            ['ai_unchecked', 'Unchecked', counts.ai_unchecked], ['checked', 'Checked', counts.checked]].map(([value, label, n]) => (
            <button key={value} type="button" aria-pressed={filter === value} onClick={() => setFilter(value)}>
              {label} <span className="num text-muted">{n}</span>
            </button>
          ))}
        </div>
        <button type="button" className="btn btn-primary" disabled={running !== null || missing.length === 0}
                onClick={() => setAsking({ ids: missing, replaces: false })}>
          Estimate {missing.length} with AI
        </button>
      </div>

      {running && (
        <div className="card space-y-2.5 px-5 py-4" role="status" aria-live="polite">
          <div className="flex items-center justify-between gap-3 text-sm">
            <span className="font-semibold">Estimating recipes</span>
            <span className="flex items-center gap-3">
              <span className="num text-muted">
                {running.done} of {running.total}{running.failed > 0 && ` · ${running.failed} failed`}
              </span>
              <button type="button" className="btn btn-secondary btn-sm" onClick={() => { stop.current = true }}>Stop</button>
            </span>
          </div>
          <div className="progress" role="progressbar" aria-label="Estimating recipes"
               aria-valuemin={0} aria-valuemax={running.total} aria-valuenow={running.done}>
            <div className="progress-bar" style={{ width: `${(running.done / running.total) * 100}%` }} />
          </div>
        </div>
      )}
      {error && <p className="alert-error">{error}</p>}

      <Card flush>
        <div className="overflow-x-auto">
          <table className="table min-w-[820px]">
            <thead>
              <tr>
                <th>Dish</th>
                <th className="text-right">Price</th>
                <th className="text-right">Plate cost</th>
                <th className="text-right">Food cost</th>
                <th>Status</th>
                <th>Checks</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {shown.map((row) => {
                const [tone, label] = STATUS[row.status]
                const working = busy.has(row.dish_id)
                const checks = row.status === 'ai_unchecked' ? row.checks : []
                return [
                  <tr key={row.dish_id}>
                    <td>
                      <span className="font-semibold">{row.name}</span>
                      <span className="block text-xs text-muted">{row.category ?? 'No category'}</span>
                    </td>
                    <td className="num text-right">{pounds(row.menu_price)}</td>
                    <td className="num text-right text-muted">{row.plate_cost != null ? pounds(row.plate_cost) : '—'}</td>
                    <td className="num text-right">{row.food_cost_percent != null ? percent(row.food_cost_percent, 0) : '—'}</td>
                    <td>
                      {working ? (
                        <span className="flex items-center gap-2 text-sm text-muted">
                          <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-line border-t-accent" aria-hidden="true" />
                          Estimating
                        </span>
                      ) : <span className={`chip ${tone}`}>{label}</span>}
                    </td>
                    <td>
                      <div className="flex flex-wrap gap-1.5">
                        {errors[row.dish_id] && (
                          <Hint content={errors[row.dish_id]}><span className="chip chip-warn">Failed</span></Hint>
                        )}
                        {row.recipe_check && (
                          <Hint content="The menu description changed. Check the recipe still matches.">
                            <span className="chip chip-warn">Check recipe</span>
                          </Hint>
                        )}
                        {checks.map((c) => {
                          const [chipLabel, hint] = checkChip(c, row)
                          return <Hint key={c} content={hint}><span className="chip chip-warn">{chipLabel}</span></Hint>
                        })}
                      </div>
                    </td>
                    <td className="whitespace-nowrap text-right">
                      <RowButton label="Estimate with AI" disabled={working || running !== null}
                                 onClick={() => setAsking({ ids: [row.dish_id], name: row.name, replaces: row.status !== 'none' })}>estimate</RowButton>
                      <RowButton label={open?.id === row.dish_id ? 'Close' : 'Edit recipe'} disabled={working}
                                 onClick={() => edit(row.dish_id)}>{open?.id === row.dish_id ? 'close' : 'edit'}</RowButton>
                      {row.status === 'ai_unchecked' && (
                        <RowButton label="Looks right" disabled={working} onClick={() => looksRight(row.dish_id)}>looks right</RowButton>
                      )}
                    </td>
                  </tr>,
                  open?.id === row.dish_id && (
                    <tr key={`${row.dish_id}-edit`}>
                      <td colSpan={7} className="bg-bg">
                        {open.dish
                          ? <RecipeEditor dish={open.dish} ingredients={ingredients} onSaved={saved} />
                          : <p className="text-muted">Loading…</p>}
                      </td>
                    </tr>
                  ),
                ]
              })}
            </tbody>
          </table>
        </div>
      </Card>

      <ConfirmDialog
        open={asking !== null}
        title={asking?.name ? `Estimate ${asking.name} with AI?` : `Estimate ${asking?.ids.length} recipes with AI?`}
        confirmLabel="Estimate"
        onConfirm={() => estimate(asking.ids)}
        onCancel={() => setAsking(null)}
      >
        {asking?.replaces ? 'The current recipe is replaced. ' : ''}
        {asking?.ids.length === 1 ? 'It is' : 'Each is'} saved as an unchecked AI estimate.
      </ConfirmDialog>
    </div>
  )
}

export default RecipesTable
