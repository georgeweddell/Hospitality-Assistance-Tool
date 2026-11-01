import Delta from './Delta'
import Hint from './Hint'
import TicketRail from './TicketRail'
import { PriceRiseList } from './PriceChanges'
import { usePriceChanges } from '../priceChanges'
import { useSuggestions } from '../suggestions'
import { useEffect, useState } from 'react'
import { getJson } from '../api'
import { rangeQuery } from '../dateRange'
import { pounds, shortDate } from '../format'
import { QUADRANTS, quadrantTextColor } from '../quadrants'
import { percent, poundsRounded } from '../format'
import { previousLabel, rangeLabel } from '../dateRange'
import { IMPACT_EXPLAINED } from '../actionText'
import { navigate } from '../useHashRoute'
import { pctChange, summarise } from '../figures'

// £36,036 → £36k for the big figure (the full amount sits underneath).
const short = (v) => (Math.abs(v) >= 10000 ? `£${Math.round(v / 1000)}k` : poundsRounded(v))

// Tiles in the same places as the chart's zones: Puzzles top left, Stars top right.
const TILES = ['Puzzle', 'Star', 'Dog', 'Plowhorse']
// Lower is better, for marking a move up or down.
const STANDING = { Star: 0, Plowhorse: 1, Puzzle: 1, Dog: 2 }

// How each dish changed since the previous period: 'new', '↑', '↓' or '→'
// (a sideways move, Plowhorse ↔ Puzzle), plus how many dishes left.
function movesSince(dishes, prevDishes) {
  const prevById = Object.fromEntries(prevDishes.map((d) => [d.dish_id, d]))
  const nowIds = new Set(dishes.map((d) => d.dish_id))
  const moves = {}
  for (const d of dishes) {
    const p = prevById[d.dish_id]
    if (!p) moves[d.dish_id] = { mark: 'new' }
    else if (p.quadrant !== d.quadrant) {
      const diff = STANDING[d.quadrant] - STANDING[p.quadrant]
      moves[d.dish_id] = { mark: diff < 0 ? '↑' : diff > 0 ? '↓' : '→', from: p.quadrant }
    }
  }
  const gone = prevDishes.filter((p) => !nowIds.has(p.dish_id)).length
  return { moves, gone }
}

function DishPill({ dish, move }) {
  const style = !move ? 'bg-bg'
    : move.mark === 'new' ? 'bg-ink text-bg'
    : move.mark === '↓' ? 'bg-accent text-accent-ink'
    : 'bg-basil text-bg'
  const title = move?.from ? `Was ${move.from}` : move ? 'New' : undefined
  return (
    // One line; on a narrow tile a long name is cut short with "…" (the full name is in the title).
    <a href={`#/menu/${dish.dish_id}`} title={title ? `${dish.dish_name} · ${title}` : dish.dish_name}
       className={`inline-block max-w-full truncate rounded-full px-2.5 py-1 text-[0.8125rem] hover:underline ${style}`}>
      {move && move.mark !== 'new' && `${move.mark} `}{dish.dish_name}{move?.mark === 'new' && ' · new'}
    </a>
  )
}

// Opens the Menu page on its Recipes tab.
function openRecipes() {
  try {
    sessionStorage.setItem('menu-view', JSON.stringify({ category: 'recipes', status: 'all' }))
  } catch {
    // the Menu page opens on its default tab instead
  }
  navigate('menu')
}

// Menu price changes from the start of the period to today (backend: price_changes.py).
function useMenuPriceChanges(range, reload) {
  const [changes, setChanges] = useState(null)
  useEffect(() => {
    let ignore = false
    getJson(`/menu-price-changes?${rangeQuery(range)}`)
      .then((rows) => { if (!ignore) setChanges(rows) })
      .catch(() => { if (!ignore) setChanges([]) })
    return () => { ignore = true }
  }, [range, reload])
  return changes
}

// The overview's buttons and links, shown in the title row (App.jsx → Layout's
// `actions`) so they don't take a row of their own above the tiles.
export function OverviewActions({ dishes, range, unchecked = 0 }) {
  const checks = useSuggestions(range, dishes)
  const firing = checks ? checks.filter((c) => c.fires).length : 0
  return (
    <>
      {unchecked > 0 && (
        <span className="flex items-center gap-2">
          <button type="button" onClick={openRecipes} className="chip chip-accent num">
            {unchecked} unchecked AI recipe{unchecked === 1 ? '' : 's'}
          </button>
          <Hint label="About unchecked recipes"
                content="Recipes estimated by AI and not yet checked. Their costs are estimates until you check them." />
        </span>
      )}
      {firing > 0 && (
        <a href="#/reports/suggestions" className="link text-sm font-normal">
          {firing} business suggestion{firing === 1 ? '' : 's'} →
        </a>
      )}
      <a href="#/reports" className="btn btn-primary">Generate report</a>
    </>
  )
}

function OverviewPage({ dishes, prevDishes, actions, range }) {
  const priceChanges = usePriceChanges(range, dishes)
  const menuPrices = useMenuPriceChanges(range, dishes)
  const now = summarise(dishes)
  const hasPrev = prevDishes.length > 0
  const before = hasPrev ? summarise(prevDishes) : null
  const vs = previousLabel(range)
  const onPrev = (v) => `${v}% on ${vs.toLowerCase()}`   // every change says what it compares with

  const dishById = Object.fromEntries(dishes.map((d) => [d.dish_id, d]))
  const { moves, gone } = hasPrev ? movesSince(dishes, prevDishes) : { moves: {}, gone: 0 }
  const moved = Object.values(moves).filter((m) => m.mark !== 'new').length
  const added = Object.values(moves).filter((m) => m.mark === 'new').length
  const sinceParts = [moved && `${moved} moved`, added && `${added} new`, gone && `${gone} gone`].filter(Boolean)

  return (
    <div className="space-y-8">

      <section className="grid gap-4 lg:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)]">
        <div className="tile tile-tomato min-h-[300px] px-8 py-7">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="tile-label">contribution · {rangeLabel(range).toLowerCase()}</span>
            {hasPrev && <Delta onTile value={pctChange(now.contribution, before.contribution)} format={onPrev} />}
          </div>
          <span className="figure figure-hero -ml-0.5 text-[clamp(4rem,8vw,6.5rem)]">{short(now.contribution)}</span>
          <span className="tile-label num">{poundsRounded(now.contribution)} · {dishes.length} dishes</span>
        </div>
        <div className="grid grid-cols-2 gap-4">
          {/* Paper tiles: the contribution tile is the one bright thing here. */}
          <div className="tile tile-paper">
            <span className="tile-label">sales</span>
            <span className="figure text-[clamp(2rem,3vw,2.5rem)]">{poundsRounded(now.sales)}</span>
            {hasPrev ? <span><Delta value={pctChange(now.sales, before.sales)} format={onPrev} /></span> : <span />}
          </div>
          <div className="tile tile-paper">
            <span className="tile-label">dishes sold</span>
            <span className="figure text-[clamp(2rem,3vw,2.5rem)]">{now.units.toLocaleString('en-GB')}</span>
            {hasPrev ? <span><Delta value={pctChange(now.units, before.units)} format={onPrev} /></span> : <span />}
          </div>
          <div className="tile tile-outline col-span-2 flex-row items-center">
            <div className="flex flex-col items-start gap-2">
              <span className="tile-label">gross margin</span>
              {hasPrev && <Delta value={now.grossMargin - before.grossMargin} format={(v) => `${v} pts on ${vs.toLowerCase()}`} />}
            </div>
            <span className="figure text-[clamp(2rem,3vw,2.5rem)]">{percent(now.grossMargin)}</span>
          </div>
        </div>
      </section>

      <div className="grid gap-10 lg:grid-cols-[minmax(0,1.15fr)_minmax(0,0.85fr)]">
        <section className="min-w-0 space-y-4">
          <div className="flex items-baseline justify-between gap-2">
            <div className="flex items-center gap-2">
              <h2 className="section-title text-[1.75rem]">recommended changes</h2>
              <Hint content={IMPACT_EXPLAINED} label="How impact is worked out" />
            </div>
            {actions.length > 0 && <a href="#/actions" className="link whitespace-nowrap text-sm font-normal">all {actions.length} →</a>}
          </div>
          {actions.length === 0 ? (
            <div className="empty">No changes</div>
          ) : (
            <TicketRail actions={actions.slice(0, 3)} categoryOf={(id) => dishById[id]?.category} />
          )}
        </section>

        <section className="space-y-4">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <h2 className="section-title text-[1.75rem]">quadrants</h2>
            {hasPrev && sinceParts.length > 0 && (
              <span className="text-sm text-muted">since {vs.toLowerCase()}: {sinceParts.join(' · ')}</span>
            )}
          </div>
          <div className="grid grid-cols-2 gap-2.5">
            {TILES.map((q) => {
              const members = dishes.filter((d) => d.quadrant === q)
              // Paper tiles: the quadrant's colour is on its name and dot, not the whole tile.
              return (
                <div key={q} className="tile tile-paper justify-start gap-2.5 p-4">
                  <div className="flex items-baseline justify-between">
                    <Hint content={QUADRANTS[q].meaning}>
                      <span className="flex items-center gap-1.5 font-semibold" style={{ color: quadrantTextColor(q) }}>
                        <span className="h-2 w-2 rounded-full" style={{ backgroundColor: quadrantTextColor(q) }} aria-hidden="true" />
                        {q.toLowerCase()}s
                      </span>
                    </Hint>
                    <span className="num text-lg font-medium">{members.length}</span>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {members.map((d) => <DishPill key={d.dish_id} dish={d} move={moves[d.dish_id]} />)}
                  </div>
                </div>
              )
            })}
          </div>
        </section>
      </div>

      <section className="grid gap-4 lg:grid-cols-2">
        <div className="card">
          <div className="card-header">
            <h2 className="section-title">ingredient price rises</h2>
            {priceChanges && <span className="count">{priceChanges.filter((c) => c.is_alert).length}</span>}
          </div>
          {priceChanges ? <PriceRiseList changes={priceChanges} /> : <p className="card-body text-muted">Loading…</p>}
        </div>
        <div className="card">
          <div className="card-header">
            <h2 className="section-title">menu price changes</h2>
            {menuPrices && <span className="count">{menuPrices.length}</span>}
          </div>
          {!menuPrices ? <p className="card-body text-muted">Loading…</p>
            : menuPrices.length === 0 ? <p className="card-body text-sm text-muted">none</p>
            : (
              <ul>
                {menuPrices.slice(0, 5).map((c) => (
                  <li key={`${c.dish_id}-${c.day}`}
                      className="flex items-baseline justify-between gap-4 border-t border-hairline px-5 py-3">
                    <a href={`#/menu/${c.dish_id}`} className="font-semibold hover:underline">{c.name}</a>
                    <span className="num text-sm">{pounds(c.old_price)} → {pounds(c.new_price)}</span>
                    <span className="num text-xs text-muted">{shortDate(c.day).toLowerCase()}</span>
                  </li>
                ))}
              </ul>
            )}
        </div>
      </section>
    </div>
  )
}

export default OverviewPage
