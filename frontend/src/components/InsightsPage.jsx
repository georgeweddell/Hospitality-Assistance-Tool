import { useState } from 'react'
import Card from './Card'
import Delta from './Delta'
import Hint from './Hint'
import QuadrantBadge from './QuadrantBadge'
import QuadrantChart from './QuadrantChart'
import { CATEGORIES } from '../categories'
import { IMPACT_EXPLAINED, VERB, explain } from '../actionText'
import { pctChange, summarise } from '../figures'
import { pounds, poundsRounded } from '../format'
import { isFullMonth, previousLabel } from '../dateRange'

// Insights: one menu-engineering chart, filtered by a dropdown that starts on
// all categories, with the highlights beside it (top earner, biggest
// opportunity, what moved) and the figures against the previous period
// underneath. Everything follows the filter.

const PLURAL = { Starter: 'Starters', Main: 'Mains', Side: 'Sides', Dessert: 'Desserts' }

// The chosen filter survives a reload in this tab (storage can be unavailable).
const STORAGE_KEY = 'insights-category'
function loadCategory() {
  try {
    return sessionStorage.getItem(STORAGE_KEY)
  } catch {
    return null
  }
}
function saveCategory(category) {
  try {
    sessionStorage.setItem(STORAGE_KEY, category)
  } catch {
    // not important enough to surface
  }
}

function Figure({ label, value, children }) {
  return (
    <div className="tile tile-outline">
      <span className="tile-label">{label}</span>
      <span className="figure text-[clamp(2.25rem,3.5vw,3.25rem)]">{value}</span>
      <div className="min-h-[22px]">{children}</div>
    </div>
  )
}

const DishLink = ({ id, name }) => (
  <a href={`#/menu/${id}`} className="figure text-[2.5rem] hover:underline">{name}</a>
)

function InsightsPage({ dishes, prevDishes, actions, range }) {
  const present = CATEGORIES.filter((c) => dishes.some((d) => d.category === c))
  const [chosen, setChosen] = useState(loadCategory)
  const category = present.includes(chosen) ? chosen : null   // null: all categories
  const choose = (value) => {
    setChosen(value)
    saveCategory(value)
  }

  const inCategory = category ? dishes.filter((d) => d.category === category) : dishes
  const prevInCategory = category ? prevDishes.filter((d) => d.category === category) : prevDishes
  const prevById = Object.fromEntries(prevDishes.map((d) => [d.dish_id, d]))
  const byId = Object.fromEntries(inCategory.map((d) => [d.dish_id, d]))
  const hasPrev = prevDishes.length > 0
  const since = previousLabel(range)

  // Highlights
  const earner = inCategory.reduce((best, d) =>
    (!best || d.margin_pounds * d.units_sold > best.margin_pounds * best.units_sold ? d : best), null)
  const opportunity = actions.find((a) => byId[a.dish_id])
  const moved = inCategory
    .filter((d) => prevById[d.dish_id] && prevById[d.dish_id].quadrant !== d.quadrant)
    .sort((a, b) => (b.quadrant === 'Star') - (a.quadrant === 'Star'))
  const labelled = new Set([earner?.dish_id, opportunity?.dish_id, ...moved.slice(0, 3).map((d) => d.dish_id)].filter(Boolean))

  const now = summarise(inCategory)
  const before = summarise(prevInCategory)
  const compare = hasPrev && prevInCategory.length > 0

  return (
    <div className="space-y-5">
      <select value={category ?? 'all'} onChange={(e) => choose(e.target.value)} className="input input-pill w-auto"
              aria-label="Show">
        <option value="all">all categories ({dishes.length})</option>
        {present.map((c) => (
          <option key={c} value={c}>{PLURAL[c].toLowerCase()} ({dishes.filter((d) => d.category === c).length})</option>
        ))}
      </select>

      <div className="grid gap-5 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
        {/* A fresh chart per filter: Recharts can otherwise ask for labels of dots that have gone */}
        <QuadrantChart key={category ?? 'all'} dishes={dishes} category={category} labelled={labelled} />

        <div className="space-y-5">
          {earner && (
            <div className="tile tile-basil corner-bl">
              <span className="flex items-center justify-between gap-2">
                <span className="tile-label">top earner</span>
                <Hint align="right" label="About top earner" content="Margin × units sold: what the dish contributed over the period." />
              </span>
              <DishLink id={earner.dish_id} name={earner.dish_name} />
              <span className="tile-label num">
                {poundsRounded(earner.margin_pounds * earner.units_sold)} · {earner.units_sold} sold · {pounds(earner.margin_pounds)} margin
              </span>
            </div>
          )}

          <div className="tile tile-tomato corner-tl">
            <span className="flex items-center justify-between gap-2">
              <span className="tile-label">biggest opportunity</span>
              <Hint align="right" label="About the opportunity" content={IMPACT_EXPLAINED} />
            </span>
            {opportunity ? (
              <>
                <DishLink id={opportunity.dish_id} name={opportunity.dish_name} />
                <Hint content={explain(byId[opportunity.dish_id])}>
                  <span className="tile-label num">
                    {VERB[opportunity.quadrant].toLowerCase()} · +{poundsRounded(opportunity.impact_pounds)}{isFullMonth(range) && ' / month'}
                  </span>
                </Hint>
              </>
            ) : <span className="tile-label">none</span>}
          </div>

          <Card title={`Since ${since}`} flush>
            {!hasPrev ? (
              <p className="card-body text-muted">No earlier data</p>
            ) : moved.length === 0 ? (
              <p className="card-body text-muted">No quadrant changes</p>
            ) : (
              <ul className="divide-y-[1.5px] divide-dashed divide-line-strong border-t-[1.5px] border-dashed border-line-strong">
                {moved.map((d) => (
                  <li key={d.dish_id} className="flex flex-wrap items-center justify-between gap-2 px-5 py-3">
                    <a href={`#/menu/${d.dish_id}`} className="font-semibold hover:text-accent">{d.dish_name}</a>
                    <span className="flex items-center gap-1.5 text-muted">
                      <QuadrantBadge quadrant={prevById[d.dish_id].quadrant} /> → <QuadrantBadge quadrant={d.quadrant} />
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Figure label="Contribution" value={poundsRounded(now.contribution)}>
          {compare && <Delta value={pctChange(now.contribution, before.contribution)} />}
        </Figure>
        <Figure label="Sales" value={poundsRounded(now.sales)}>
          {compare && <Delta value={pctChange(now.sales, before.sales)} />}
        </Figure>
        <Figure label="Margin per dish sold" value={pounds(now.avgMargin)}>
          {/* in pence, so Delta's one-decimal rounding keeps a few pence exact */}
          {compare && <Delta value={(now.avgMargin - before.avgMargin) * 100} format={(v) => `£${(v / 100).toFixed(2)}`} />}
        </Figure>
        <Figure label="Dishes sold" value={now.units.toLocaleString('en-GB')}>
          {compare && <Delta value={pctChange(now.units, before.units)} />}
        </Figure>
      </div>
    </div>
  )
}

export default InsightsPage
