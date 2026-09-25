import { useEffect, useState } from 'react'
import Card from './Card'
import ConfirmDialog from './ConfirmDialog'
import DishForm from './DishForm'
import MenuPrices from './MenuPrices'
import Hint from './Hint'
import QuadrantBadge from './QuadrantBadge'
import RecipeEditor from './RecipeEditor'
import { deleteJson, getJson, putJson } from '../api'
import { navigate } from '../useHashRoute'
import { percent, pounds, shortDate } from '../format'
import { rangeLabel, rangeQuery } from '../dateRange'

function menuDates(dish) {
  return dish.on_menu_until
    ? `On the menu ${shortDate(dish.on_menu_from)} – ${shortDate(dish.on_menu_until)}`
    : `On the menu since ${shortDate(dish.on_menu_from)}`
}

function Stat({ label, value }) {
  return (
    <div className="card flex flex-col gap-2.5 px-5 py-[18px]">
      <p className="label">{label}</p>
      <p className="stat-value text-[1.625rem]">{value}</p>
    </div>
  )
}

function DishPage({ dishId, range, analysed, onChanged }) {
  const [dish, setDish] = useState(null)
  const [ingredients, setIngredients] = useState(null)
  const [error, setError] = useState(null)
  const [editing, setEditing] = useState(false)
  const [confirmingDelete, setConfirmingDelete] = useState(false)
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
    deleteJson(`/dishes/${dishId}`)
      .then(() => {
        setConfirmingDelete(false)
        onChanged()
        navigate('menu')
      })
      .catch((err) => {
        setConfirmingDelete(false)
        setError(err.message)
      })
  }

  const back = <a href="#/menu" className="text-sm font-medium text-muted hover:text-ink">← Menu</a>

  if (error) {
    return (
      <div className="space-y-4">
        {back}
        <p className="alert-error">{error}</p>
      </div>
    )
  }
  if (!dish || !ingredients) return <p className="text-muted">Loading dish…</p>

  const quadrant = analysed?.quadrant

  return (
    <div className="space-y-6">
      {back}

      {editing ? (
        <Card title="Edit details">
          <DishForm initial={dish} submitLabel="Save" onSubmit={saveDetails} onCancel={() => setEditing(false)} />
        </Card>
      ) : (
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="flex flex-wrap items-center gap-3">
              <h1 className="page-title">{dish.name}</h1>
              {quadrant && <QuadrantBadge quadrant={quadrant} />}
              {dish.recipe_check && (
                <Hint content="The menu description changed on a menu import. Check the recipe still matches; saving the recipe clears this.">
                  <span className="chip chip-warn">Check recipe</span>
                </Hint>
              )}
            </div>
            <p className="num mt-2 text-muted">
              {dish.category ?? 'No category'} · {pounds(dish.menu_price)} · {menuDates(dish)}
            </p>
            {dish.description && <p className="mt-1 text-sm text-muted">{dish.description}</p>}
          </div>
          <div className="flex gap-2">
            <button type="button" onClick={() => setEditing(true)} className="btn btn-secondary">Edit details</button>
            <button type="button" onClick={() => setConfirmingDelete(true)} className="btn btn-danger">Delete</button>
          </div>
        </div>
      )}

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Stat label="Plate cost" value={dish.lines.length ? pounds(dish.cost.plate_cost) : '—'} />
        <Stat label="Margin" value={dish.lines.length ? pounds(dish.cost.margin_pounds) : '—'} />
        <Stat label="Gross margin" value={dish.lines.length ? percent(dish.cost.margin_percent) : '—'} />
        <Stat label={`Sold · ${rangeLabel(range)}`} value={dish.units_sold} />
      </div>

      <RecipeEditor key={loads} dish={dish} ingredients={ingredients} onSaved={reload} />

      {dish.prices.length > 1 && <MenuPrices dishId={dish.id} prices={dish.prices} onChanged={reload} />}

      <ConfirmDialog open={confirmingDelete} title={`Delete ${dish.name}?`} confirmLabel="Delete"
                     onConfirm={remove} onCancel={() => setConfirmingDelete(false)}>
        Its recipe and sales records are deleted too. This can't be undone.
      </ConfirmDialog>
    </div>
  )
}

export default DishPage
