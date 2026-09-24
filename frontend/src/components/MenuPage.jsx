import { useState } from 'react'
import Card from './Card'
import DishForm from './DishForm'
import QuadrantBadge from './QuadrantBadge'
import { CATEGORIES } from '../categories'
import { QUADRANT_ORDER } from '../quadrants'
import { postJson } from '../api'
import { navigate } from '../useHashRoute'
import { percent, pounds } from '../format'

const INPUT = 'rounded-lg border border-line bg-surface px-3 py-2 text-sm text-ink focus:border-accent focus:outline-none'

// Short labels for the reasons a dish isn't analysed yet.
const MISSING = {
  'No category set': 'Needs category',
  'No recipe saved': 'Needs recipe',
  'No sales data': 'Needs sales',
}

const PLURAL = { Starter: 'Starters', Main: 'Mains', Side: 'Sides', Dessert: 'Desserts' }

// Remember the chosen tab and filter, so "← Menu" from a dish page comes back
// to the same view. Browser storage can be unavailable, so failures are ignored.
const STORAGE_KEY = 'menu-view'
function loadView() {
  try {
    return JSON.parse(sessionStorage.getItem(STORAGE_KEY)) ?? {}
  } catch {
    return {}
  }
}
function saveView(view) {
  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(view))
  } catch {
    // not important enough to surface
  }
}

const MUTED_CHIP = 'whitespace-nowrap rounded-full bg-line/60 px-2 py-0.5 text-xs text-muted'

// On the menu for at least part of the range (ISO date strings compare correctly as text).
function onMenuDuring(dish, range) {
  return dish.on_menu_from <= range.to && (!dish.on_menu_until || dish.on_menu_until >= range.from)
}

function Status({ dish, range, analysed, reasons }) {
  if (analysed) return <QuadrantBadge quadrant={analysed.quadrant} />
  if (reasons.length === 0) {
    // Complete, but not analysed: either off the menu, or no sales recorded in the period at all.
    return <span className={MUTED_CHIP}>{onMenuDuring(dish, range) ? 'No sales in this period' : 'Not on the menu'}</span>
  }
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

function DishTable({ dishes, range, analysedById, reasonsById }) {
  return (
    <div className="overflow-x-auto">
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
              <tr key={dish.id} onClick={() => navigate(`menu/${dish.id}`)}
                  className="cursor-pointer border-b border-line last:border-0 hover:bg-bg">
                <td className="py-3 pl-5 pr-3">
                  <a href={`#/menu/${dish.id}`} className="block truncate font-medium hover:text-accent">{dish.name}</a>
                </td>
                <td className="px-3 py-3 text-right tabular-nums">{pounds(dish.menu_price)}</td>
                <td className="px-3 py-3 text-right tabular-nums text-muted">{a ? pounds(a.plate_cost) : '—'}</td>
                <td className="px-3 py-3 text-right tabular-nums">{a ? percent(a.margin_percent) : '—'}</td>
                <td className="py-3 pl-3 pr-5"><Status dish={dish} range={range} analysed={a} reasons={reasonsById[dish.id] ?? []} /></td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

function MenuPage({ allDishes, analysed, incomplete, range, onChanged }) {
  // Statuses are for the chosen period: a dish off the menu then shows "Not on the menu".
  const saved = loadView()
  const [category, setCategory] = useState(saved.category ?? CATEGORIES.find((c) => allDishes.some((d) => d.category === c)) ?? 'all')
  const [status, setStatus] = useState(saved.status && saved.status !== 'attention' ? saved.status : 'all')
  const [search, setSearch] = useState('')
  const [adding, setAdding] = useState(false)

  const choose = (view) => {
    const next = { category, status, ...view }
    if (view.category !== undefined) setCategory(view.category)
    if (view.status !== undefined) setStatus(view.status)
    saveView({ category: next.category, status: next.status })
  }

  const analysedById = Object.fromEntries(analysed.map((d) => [d.dish_id, d]))
  const reasonsById = Object.fromEntries(incomplete.map((d) => [d.dish_id, d.reasons]))

  const hasUncategorised = allDishes.some((d) => !d.category)
  const tabs = [
    ...CATEGORIES.map((c) => ({ value: c, label: PLURAL[c], count: allDishes.filter((d) => d.category === c).length })),
    ...(hasUncategorised ? [{ value: 'none', label: 'No category', count: allDishes.filter((d) => !d.category).length }] : []),
    { value: 'all', label: 'All', count: allDishes.length },
    { value: 'attention', label: 'Needs attention', count: incomplete.length, warn: true },
  ]

  const inCategory = allDishes.filter((d) =>
    category === 'all' ? true
      : category === 'attention' ? Boolean(reasonsById[d.id])
      : category === 'none' ? !d.category
      : d.category === category)
  const onAttentionTab = category === 'attention'

  const term = search.trim().toLowerCase()
  const shown = inCategory
    .filter((d) => d.name.toLowerCase().includes(term))
    .filter((d) => onAttentionTab || status === 'all' || analysedById[d.id]?.quadrant === status)
    .sort((a, b) => a.name.localeCompare(b.name))

  // Summary for the selected tab (analysed dishes only have a margin).
  const analysedHere = inCategory.map((d) => analysedById[d.id]).filter(Boolean)
  const avgMargin = analysedHere.length
    ? analysedHere.reduce((s, d) => s + d.margin_percent, 0) / analysedHere.length
    : null
  const attentionHere = inCategory.filter((d) => reasonsById[d.id]).length

  const addDish = (fields) =>
    postJson('/dishes', fields).then((dish) => {
      setAdding(false)
      onChanged()
      navigate(`menu/${dish.id}`)  // straight to the new dish, to add its recipe
    })

  // Views that span categories are grouped by category so they stay readable.
  const grouped = category === 'all' || onAttentionTab
    ? [...CATEGORIES, null]
        .map((c) => ({ c, dishes: shown.filter((d) => (d.category ?? null) === c) }))
        .filter((g) => g.dishes.length > 0)
    : null

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3 border-b border-line">
        <nav className="-mb-px flex gap-1 overflow-x-auto" aria-label="Menu categories">
          {tabs.map((t) => (
            <button
              key={t.value}
              type="button"
              onClick={() => choose({ category: t.value })}
              aria-current={category === t.value ? 'page' : undefined}
              className={`whitespace-nowrap border-b-2 px-3 py-2 text-sm ${
                category === t.value ? 'border-accent font-medium text-ink' : 'border-transparent text-muted hover:text-ink'
              }`}
            >
              {t.label}
              <span className={`ml-1.5 rounded-full px-1.5 text-xs tabular-nums ${
                t.warn && t.count > 0 ? 'bg-warn-bg font-medium text-warn' : 'bg-line/60 text-muted'
              }`}>{t.count}</span>
            </button>
          ))}
        </nav>
        {!adding && (
          <button type="button" onClick={() => setAdding(true)}
                  className="mb-2 rounded-lg bg-accent px-4 py-2 text-sm font-medium text-accent-ink hover:opacity-90">
            + Add dish
          </button>
        )}
      </div>

      {adding && (
        <Card title="New dish">
          <DishForm
            initial={{ category: CATEGORIES.includes(category) ? category : '' }}
            submitLabel="Add dish"
            onSubmit={addDish}
            onCancel={() => setAdding(false)}
          />
        </Card>
      )}

      <div className="flex flex-wrap items-center justify-between gap-3">
        {onAttentionTab ? (
          <p className="text-sm text-muted">
            These dishes are left out of the analysis until they have a category, a recipe and sales.
          </p>
        ) : (
          <p className="text-sm text-muted">
            <span className="font-medium text-ink">{inCategory.length} dish{inCategory.length === 1 ? '' : 'es'}</span>
            {avgMargin != null && <> · average margin <span className="font-medium text-ink">{percent(avgMargin)}</span></>}
            {attentionHere > 0 && (
              <>
                {' · '}
                <button type="button" onClick={() => choose({ category: 'attention' })} className="text-warn hover:underline">
                  {attentionHere} need{attentionHere === 1 ? 's' : ''} attention
                </button>
              </>
            )}
          </p>
        )}
        <div className="flex flex-wrap gap-2">
          <input type="search" value={search} onChange={(e) => setSearch(e.target.value)}
                 placeholder="Search dishes" className={`${INPUT} w-48`} aria-label="Search dishes" />
          {!onAttentionTab && (
            <select value={status} onChange={(e) => choose({ status: e.target.value })} className={INPUT} aria-label="Filter by quadrant">
              <option value="all">All quadrants</option>
              {QUADRANT_ORDER.map((q) => <option key={q} value={q}>{q}s</option>)}
            </select>
          )}
        </div>
      </div>

      {shown.length === 0 ? (
        <div className="rounded-xl border border-dashed border-line p-8 text-center text-muted">
          {allDishes.length === 0 ? 'No dishes yet. Add your first dish to get started.'
            : onAttentionTab && !term ? 'Nothing needs attention. Every dish is analysed.'
            : 'No dishes match.'}
          {((status !== 'all' && !onAttentionTab) || term) && allDishes.length > 0 && (
            <button type="button" onClick={() => { setSearch(''); choose({ status: 'all' }) }}
                    className="ml-2 font-medium text-accent hover:underline">
              Clear filters
            </button>
          )}
        </div>
      ) : grouped ? (
        grouped.map(({ c, dishes }) => (
          <Card key={c ?? 'none'} title={c ? PLURAL[c] : 'No category'} aside={`${dishes.length}`} flush>
            <DishTable dishes={dishes} range={range} analysedById={analysedById} reasonsById={reasonsById} />
          </Card>
        ))
      ) : (
        <Card flush>
          <DishTable dishes={shown} range={range} analysedById={analysedById} reasonsById={reasonsById} />
        </Card>
      )}
    </div>
  )
}

export default MenuPage
