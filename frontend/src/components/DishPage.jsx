import { useEffect, useState } from 'react'
import Card from './Card'
import ConfirmDialog from './ConfirmDialog'
import DishForm from './DishForm'
import MenuPrices from './MenuPrices'
import Hint from './Hint'
import RecipeEditor from './RecipeEditor'
import Stamp from './Stamp'
import { Ticket } from './TicketRail'
import { explain } from '../actionText'
import { deleteJson, getJson, putJson } from '../api'
import { navigate } from '../useHashRoute'
import { percent, pounds, shortDate } from '../format'
import { rangeLabel, rangeQuery } from '../dateRange'

function menuDates(dish) {
  return dish.on_menu_until
    ? `On the menu ${shortDate(dish.on_menu_from)} – ${shortDate(dish.on_menu_until)}`
    : `On the menu since ${shortDate(dish.on_menu_from)}`
}

// One figure tile: `tone` is the tile colour class plus its odd corner.
function Stat({ label, value, sub, tone }) {
  return (
    <div className={`tile min-h-[150px] ${tone}`}>
      <span className="tile-label">{label}</span>
      <span className="figure text-[clamp(2.5rem,4.5vw,4rem)]">{value}</span>
      <span className="tile-label num">{sub}</span>
    </div>
  )
}

// `action` is this dish's recommended change for the period, if it has one;
// `actionRank` is its place in the ranked list.
function DishPage({ dishId, range, analysed, action, actionRank, onChanged }) {
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

  const back = <a href="#/menu" className="font-mono text-sm text-muted underline hover:text-ink">menu</a>

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
  const costed = dish.lines.length > 0
  const current = dish.prices.find((p) => p.effective_date <= new Date().toISOString().slice(0, 10))
  const earlier = current && dish.prices[dish.prices.indexOf(current) + 1]

  return (
    <div className="space-y-7">
      <p className="font-mono text-sm text-muted">{back} / {(dish.category ?? 'no category').toLowerCase()}</p>

      {editing ? (
        <Card title="Edit details">
          <DishForm initial={dish} submitLabel="Save" onSubmit={saveDetails} onCancel={() => setEditing(false)} />
        </Card>
      ) : (
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="flex flex-wrap items-end gap-x-6 gap-y-3">
              <h1 className="page-title text-[clamp(3.5rem,8vw,7rem)]">{dish.name}</h1>
              {quadrant && <Hint content={explain(analysed)}><Stamp quadrant={quadrant} tilt={-5} className="mb-2 text-base" /></Hint>}
              {dish.recipe_check && (
                <Hint content="The menu description changed on a menu import. Check the recipe still matches; saving the recipe clears this.">
                  <span className="chip chip-warn">Check recipe</span>
                </Hint>
              )}
            </div>
            <p className="num mt-3 text-sm text-muted">{menuDates(dish)}</p>
            {dish.description && <p className="mt-1 text-sm text-muted">{dish.description}</p>}
          </div>
          <div className="flex gap-2">
            <button type="button" onClick={() => setEditing(true)} className="btn btn-secondary">Edit details</button>
            <button type="button" onClick={() => setConfirmingDelete(true)} className="btn btn-danger">Delete</button>
          </div>
        </div>
      )}

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Stat label="menu price" value={pounds(dish.menu_price)} tone="tile-mustard corner-tr"
              sub={action?.target_price != null
                ? `target ${pounds(action.target_price)} · +${pounds(action.margin_gap)}`
                : current && earlier ? `from ${shortDate(current.effective_date)} · was ${pounds(earlier.price)}` : ''} />
        <Stat label="plate cost" value={costed ? pounds(dish.cost.plate_cost) : '—'} tone="tile-outline" />
        <Stat label="margin" value={costed ? pounds(dish.cost.margin_pounds) : '—'} tone="tile-basil"
              sub={costed ? `${percent(dish.cost.margin_percent)} gp` : ''} />
        <Stat label={`sold · ${rangeLabel(range).toLowerCase()}`} value={dish.units_sold} tone="tile-tomato corner-tl" />
      </div>

      <div className={`grid items-start gap-8 ${action || dish.prices.length > 1 ? 'lg:grid-cols-[minmax(0,1fr)_300px]' : ''}`}>
        <RecipeEditor key={loads} dish={dish} ingredients={ingredients} onSaved={reload} />
        {(action || dish.prices.length > 1) && (
          <div className="space-y-8">
            {action && (
              <div>
                <div className="rail" />
                <div className="-mt-0.5 px-6">
                  <Ticket action={action} category={dish.category} number={actionRank} tilt={1.6} href="#/actions" />
                </div>
              </div>
            )}
            {dish.prices.length > 1 && <MenuPrices dishId={dish.id} prices={dish.prices} onChanged={reload} />}
          </div>
        )}
      </div>

      <ConfirmDialog open={confirmingDelete} title={`Delete ${dish.name}?`} confirmLabel="Delete"
                     onConfirm={remove} onCancel={() => setConfirmingDelete(false)}>
        Its recipe and sales records are deleted too. This can't be undone.
      </ConfirmDialog>
    </div>
  )
}

export default DishPage
