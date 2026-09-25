import Delta from './Delta'
import Hint from './Hint'
import TicketRail from './TicketRail'
import { QUADRANTS, quadrantTextColor } from '../quadrants'
import { percent, poundsRounded } from '../format'
import { previousLabel, rangeLabel } from '../dateRange'
import { IMPACT_EXPLAINED } from '../actionText'
import { navigate } from '../useHashRoute'
import { pctChange, summarise } from '../figures'

// £36,036 → £36k for the big figure (the full amount sits underneath).
const short = (v) => (Math.abs(v) >= 10000 ? `£${Math.round(v / 1000)}k` : poundsRounded(v))

// Tiles in the same places as the chart's zones: Puzzles top left, Stars top right.
// Each keeps one round corner, the one facing the middle of the grid.
const TILES = [
  { q: 'Puzzle', corner: 'corner-tr corner-bl corner-br' },
  { q: 'Star', corner: 'corner-tl corner-bl corner-br' },
  { q: 'Dog', corner: 'corner-tl corner-tr corner-br' },
  { q: 'Plowhorse', corner: 'corner-tl corner-tr corner-bl' },
]
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
  const style = !move ? 'bg-surface'
    : move.mark === 'new' ? 'bg-ink text-bg'
    : move.mark === '↓' ? 'bg-accent text-accent-ink'
    : 'bg-basil text-bg'
  const title = move?.from ? `Was ${move.from}` : move ? 'New' : undefined
  return (
    <a href={`#/menu/${dish.dish_id}`} title={title}
       className={`rounded-full px-2.5 py-1 font-mono text-xs hover:underline ${style}`}>
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

function OverviewPage({ dishes, prevDishes, actions, range, unchecked = 0 }) {
  const now = summarise(dishes)
  const hasPrev = prevDishes.length > 0
  const before = hasPrev ? summarise(prevDishes) : null
  const vs = previousLabel(range)

  const dishById = Object.fromEntries(dishes.map((d) => [d.dish_id, d]))
  const { moves, gone } = hasPrev ? movesSince(dishes, prevDishes) : { moves: {}, gone: 0 }
  const moved = Object.values(moves).filter((m) => m.mark !== 'new').length
  const added = Object.values(moves).filter((m) => m.mark === 'new').length
  const sinceParts = [moved && `${moved} moved`, added && `${added} new`, gone && `${gone} gone`].filter(Boolean)

  return (
    <div className="space-y-8">
      {unchecked > 0 && (
        <span className="flex items-center gap-2">
          <button type="button" onClick={openRecipes} className="chip chip-accent num">
            {unchecked} unchecked AI recipe{unchecked === 1 ? '' : 's'}
          </button>
          <Hint label="About unchecked recipes"
                content="Recipes estimated by AI and not yet checked. Their costs are estimates until you check them." />
        </span>
      )}

      <section className="grid gap-4 lg:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)]">
        <div className="tile tile-tomato min-h-[300px] px-8 py-7">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="tile-label">contribution · {rangeLabel(range).toLowerCase()}</span>
            {hasPrev && <Delta onTile value={pctChange(now.contribution, before.contribution)}
                               format={(v) => `${v}% on ${vs.toLowerCase()}`} />}
          </div>
          <span className="figure -ml-1 text-[clamp(6rem,14vw,13rem)] leading-[0.8] tracking-[-0.05em]">{short(now.contribution)}</span>
          <span className="tile-label num">{poundsRounded(now.contribution)} · {dishes.length} dishes</span>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div className="tile tile-mustard">
            <span className="tile-label">sales</span>
            <span className="figure text-[clamp(2.5rem,4.5vw,4.25rem)]">{poundsRounded(now.sales)}</span>
            {hasPrev ? <span><Delta onTile value={pctChange(now.sales, before.sales)} /></span> : <span />}
          </div>
          <div className="tile tile-basil corner-bl">
            <span className="tile-label">dishes sold</span>
            <span className="figure text-[clamp(2.5rem,4.5vw,4.25rem)]">{now.units.toLocaleString('en-GB')}</span>
            {hasPrev ? <span><Delta onTile value={pctChange(now.units, before.units)} /></span> : <span />}
          </div>
          <div className="tile tile-outline col-span-2 flex-row items-center">
            <div className="flex flex-col items-start gap-2">
              <span className="tile-label">gross margin</span>
              {hasPrev && <Delta value={now.grossMargin - before.grossMargin} format={(v) => `${v} pts`} />}
            </div>
            <span className="figure text-[clamp(3rem,6vw,5.5rem)]">{percent(now.grossMargin)}</span>
          </div>
        </div>
      </section>

      <div className="grid gap-10 lg:grid-cols-[minmax(0,1.15fr)_minmax(0,0.85fr)]">
        <section className="min-w-0 space-y-4">
          <div className="flex items-baseline justify-between gap-2">
            <div className="flex items-center gap-2">
              <h2 className="section-title text-[2rem]">recommended changes</h2>
              <Hint content={IMPACT_EXPLAINED} label="How impact is worked out" />
            </div>
            {actions.length > 0 && <a href="#/actions" className="link font-mono text-sm font-normal">all {actions.length} →</a>}
          </div>
          {actions.length === 0 ? (
            <div className="empty">No changes</div>
          ) : (
            <TicketRail actions={actions.slice(0, 3)} categoryOf={(id) => dishById[id]?.category} />
          )}
        </section>

        <section className="space-y-4">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <h2 className="section-title text-[2rem]">quadrants</h2>
            {hasPrev && sinceParts.length > 0 && (
              <span className="font-mono text-sm">since {vs.toLowerCase()}: {sinceParts.join(' · ')}</span>
            )}
          </div>
          <div className="grid grid-cols-2 gap-2.5">
            {TILES.map(({ q, corner }) => {
              const members = dishes.filter((d) => d.quadrant === q)
              return (
                <div key={q} className={`flex flex-col gap-2.5 rounded-[22px] p-4 ${corner}`}
                     style={{ backgroundColor: QUADRANTS[q].tint }}>
                  <div className="flex items-baseline justify-between">
                    <Hint content={QUADRANTS[q].meaning}>
                      <span className="font-bold" style={{ color: quadrantTextColor(q) }}>{q.toLowerCase()}s</span>
                    </Hint>
                    <span className="figure text-[2rem]">{members.length}</span>
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
    </div>
  )
}

export default OverviewPage
