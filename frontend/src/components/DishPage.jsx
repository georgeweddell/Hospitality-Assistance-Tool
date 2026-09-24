import { useEffect, useState } from 'react'
import DishForm from './DishForm'
import QuadrantBadge from './QuadrantBadge'
import RecipeEditor from './RecipeEditor'
import { deleteJson, getJson, putJson } from '../api'
import { navigate } from '../useHashRoute'
import { percent, pounds, shortDate } from '../format'
import { rangeLabel, rangeQuery } from '../dateRange'

function menuDates(dish) {
  return dish.on_menu_until
    ? `on the menu ${shortDate(dish.on_menu_from)} – ${shortDate(dish.on_menu_until)}`
    : `on the menu since ${shortDate(dish.on_menu_from)}`
}

function Stat({ label, value }) {
  return (
    <div className="rounded-xl border border-line bg-surface p-4 shadow-sm">
      <p className="text-sm text-muted">{label}</p>
      <p className="mt-1 text-xl font-semibold tabular-nums">{value}</p>
    </div>
  )
}

function DishPage({ dishId, range, analysed, onChanged }) {
  const [dish, setDish] = useState(null)
  const [ingredients, setIngredients] = useState(null)
  const [error, setError] = useState(null)
  const [editing, setEditing] = useState(false)
  const [version, setVersion] = useState(0)   // bump to refetch
  // Counts completed loads. The recipe editor is keyed on it, so it restarts
  // from the saved recipe once fresh data has arrived (not before).
  const [loads, setLoads] = useState(0)

  useEffect(() => {
    let ignore = false
    Promise.all([getJson(`/dishes/${dishId}/detail?${rangeQuery(range)}`), getJson('/ingredients')])
      .then(([d, ings]) => {
        if (ignore) return
        setDish(d)
        setIngredients(ings)
        setError(null)
        setLoads((n) => n + 1)
      })
      .catch((err) => {
        if (!ignore) setError(err.message)
      })
    return () => {
      ignore = true
    }
  }, [dishId, range, version])

  const reload = () => {
    setVersion((v) => v + 1)
    onChanged()  // the dashboard figures depend on this dish too
  }

  const saveDetails = (fields) =>
    putJson(`/dishes/${dishId}`, fields).then(() => {
      setEditing(false)
      reload()
    })

  const remove = () => {
    if (!window.confirm(`Delete ${dish.name}? Its recipe and sales records are deleted too. This can't be undone.`)) return
    deleteJson(`/dishes/${dishId}`)
      .then(() => {
        onChanged()
        navigate('menu')
      })
      .catch((err) => setError(err.message))
  }

  const back = (
    <a href="#/menu" className="text-sm text-muted hover:text-ink">← Menu</a>
  )

  if (error) {
    return (
      <div className="space-y-4">
        {back}
        <p className="rounded-xl border border-danger/40 bg-surface p-5 text-danger">{error}</p>
      </div>
    )
  }
  if (!dish || !ingredients) return <p className="text-muted">Loading dish…</p>

  const quadrant = analysed?.quadrant

  return (
    <div className="space-y-6">
      {back}

      {editing ? (
        <div className="rounded-xl border border-line bg-surface p-5 shadow-sm">
          <DishForm initial={dish} submitLabel="Save" onSubmit={saveDetails} onCancel={() => setEditing(false)} />
        </div>
      ) : (
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-semibold tracking-tight">{dish.name}</h1>
              {quadrant && <QuadrantBadge quadrant={quadrant} />}
            </div>
            <p className="mt-1 text-muted">
              {dish.category ?? 'No category'} · {pounds(dish.menu_price)} · {menuDates(dish)}
            </p>
          </div>
          <div className="flex gap-2">
            <button type="button" onClick={() => setEditing(true)}
                    className="rounded-lg border border-line bg-surface px-4 py-2 text-sm hover:bg-bg">
              Edit details
            </button>
            <button type="button" onClick={remove}
                    className="rounded-lg border border-line bg-surface px-4 py-2 text-sm text-danger hover:border-danger">
              Delete
            </button>
          </div>
        </div>
      )}

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Stat label="Plate cost" value={dish.lines.length ? pounds(dish.cost.plate_cost) : '—'} />
        <Stat label="Margin" value={dish.lines.length ? pounds(dish.cost.margin_pounds) : '—'} />
        <Stat label="Gross margin" value={dish.lines.length ? percent(dish.cost.margin_percent) : '—'} />
        <Stat label={`Units sold · ${rangeLabel(range)}`} value={dish.units_sold} />
      </div>

      <RecipeEditor key={loads} dish={dish} ingredients={ingredients} onSaved={reload} />
    </div>
  )
}

export default DishPage
