import { useState } from 'react'
import Card from './Card'
import DishForm from './DishForm'
import { CATEGORIES } from '../categories'
import QuadrantBadge from './QuadrantBadge'
import { postJson } from '../api'
import { navigate } from '../useHashRoute'
import { percent, pounds } from '../format'

// Short labels for the reasons a dish isn't analysed yet.
const MISSING = {
  'No category set': 'Needs category',
  'No recipe saved': 'Needs recipe',
  'No sales data': 'Needs sales',
}

function Status({ analysed, reasons }) {
  if (analysed) return <QuadrantBadge quadrant={analysed.quadrant} />
  return (
    <div className="flex flex-wrap gap-1.5">
      {reasons.map((r) => (
        <span key={r} className="whitespace-nowrap rounded-full bg-warn-bg px-2 py-0.5 text-xs font-medium text-warn">
          {MISSING[r] ?? r}
        </span>
      ))}
    </div>
  )
}

function MenuPage({ allDishes, analysed, incomplete, onChanged }) {
  const [adding, setAdding] = useState(false)
  const [filter, setFilter] = useState('all')

  const analysedById = Object.fromEntries(analysed.map((d) => [d.dish_id, d]))
  const reasonsById = Object.fromEntries(incomplete.map((d) => [d.dish_id, d.reasons]))
  const needsAttention = allDishes.filter((d) => reasonsById[d.id])
  const shown = filter === 'attention' ? needsAttention : allDishes

  const groups = [...CATEGORIES, null]
    .map((category) => ({
      category,
      dishes: shown.filter((d) => (d.category ?? null) === category).sort((a, b) => a.name.localeCompare(b.name)),
    }))
    .filter((g) => g.dishes.length > 0)

  const addDish = (fields) =>
    postJson('/dishes', fields).then((dish) => {
      setAdding(false)
      onChanged()
      navigate(`menu/${dish.id}`)  // straight to the new dish, to add its recipe
    })

  const tab = (value, label) => (
    <button
      type="button"
      onClick={() => setFilter(value)}
      className={`rounded-lg px-3 py-1.5 text-sm ${filter === value ? 'bg-surface font-medium shadow-sm' : 'text-muted hover:text-ink'}`}
    >
      {label}
    </button>
  )

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex gap-1 rounded-xl bg-line/50 p-1">
          {tab('all', `All dishes (${allDishes.length})`)}
          {tab('attention', `Needs attention (${needsAttention.length})`)}
        </div>
        {!adding && (
          <button
            type="button"
            onClick={() => setAdding(true)}
            className="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-accent-ink hover:opacity-90"
          >
            + Add dish
          </button>
        )}
      </div>

      {adding && (
        <Card title="New dish">
          <DishForm submitLabel="Add dish" onSubmit={addDish} onCancel={() => setAdding(false)} />
        </Card>
      )}

      {groups.length === 0 && (
        <p className="rounded-xl border border-dashed border-line p-8 text-center text-muted">
          {filter === 'attention' ? 'Nothing needs attention. Every dish is analysed.' : 'No dishes yet. Add your first dish to get started.'}
        </p>
      )}

      {groups.map(({ category, dishes }) => (
        <Card key={category ?? 'none'} title={category ?? 'No category'} aside={`${dishes.length}`} flush>
          <div className="overflow-x-auto">
            {/* Fixed column widths so the columns line up across every category box. */}
            <table className="w-full min-w-[560px] table-fixed text-sm">
              <colgroup>
                <col />
                <col className="w-24" />
                <col className="w-28" />
                <col className="w-24" />
                <col className="w-44" />
              </colgroup>
              <thead>
                <tr className="border-b border-line text-xs uppercase tracking-wide text-muted">
                  <th className="py-2 pl-5 pr-3 text-left font-medium">Dish</th>
                  <th className="px-3 py-2 text-right font-medium">Price</th>
                  <th className="px-3 py-2 text-right font-medium">Plate cost</th>
                  <th className="px-3 py-2 text-right font-medium">Margin</th>
                  <th className="py-2 pl-3 pr-5 text-left font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {dishes.map((dish) => {
                  const a = analysedById[dish.id]
                  return (
                    <tr
                      key={dish.id}
                      onClick={() => navigate(`menu/${dish.id}`)}
                      className="cursor-pointer border-b border-line last:border-0 hover:bg-bg"
                    >
                      <td className="py-3 pl-5 pr-3">
                        <a href={`#/menu/${dish.id}`} className="block truncate font-medium hover:text-accent">
                          {dish.name}
                        </a>
                      </td>
                      <td className="px-3 py-3 text-right tabular-nums">{pounds(dish.menu_price)}</td>
                      <td className="px-3 py-3 text-right tabular-nums text-muted">{a ? pounds(a.plate_cost) : '—'}</td>
                      <td className="px-3 py-3 text-right tabular-nums">{a ? percent(a.margin_percent) : '—'}</td>
                      <td className="py-3 pl-3 pr-5"><Status analysed={a} reasons={reasonsById[dish.id] ?? []} /></td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </Card>
      ))}
    </div>
  )
}

export default MenuPage
