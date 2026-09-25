// Wording for actions, shared by the Overview's move cards and the Actions page.
// Only short labels appear on screen; explanations are shown on demand (Hint).
import { percent, pounds } from './format'

// The concrete change on an action (backend: menu_engineering.proposed_change):
//   { text: '£11.50 → £12.40', hint: why }  for a price (Plowhorse, Dog)
//   { text: '+91 plates · 2.9 a day', hint } for sales (Puzzle)
// null when there's nothing to show (e.g. already repriced past the line).
export function proposal(action) {
  if (action.target_price != null) {
    return {
      text: `${pounds(action.current_price)} → ${pounds(action.target_price)}`,
      hint: `The price that brings its margin up to the category average: plate cost + average margin. ` +
        `Or cut the plate cost by ${pounds(action.margin_gap)}. Starts from today's price, including VAT.`,
    }
  }
  if (action.extra_units != null) {
    const perDay = action.extra_per_day.toFixed(1)
    return {
      text: `+${action.extra_units} plates · ${perDay} a day`,
      hint: `Extra plates over the period to reach its category's popularity line, about ${perDay} a day.`,
    }
  }
  return null
}

// Short verb for each action, used as the Actions filter labels.
export const VERB = { Plowhorse: 'Reprice', Puzzle: 'Promote', Dog: 'Review' }

// Why the dish is in its quadrant (the numbers against the lines) and what to do.
export function explain(dish) {
  if (!dish) return ''
  const mix = `${percent(dish.menu_mix_percent)} of sales (popular from ${percent(dish.popularity_threshold)})`
  const margin = `${pounds(dish.margin_pounds)} margin (profitable from ${pounds(dish.profitability_threshold)})`
  const verdict = {
    Star: 'Popular and profitable. Keep it and feature it.',
    Plowhorse: 'Popular but below the margin line. Reprice it or rework the recipe.',
    Puzzle: 'Profitable but not selling enough. Promote it or reposition it on the menu.',
    Dog: 'Below both lines. Consider cutting it.',
  }[dish.quadrant]
  return `${verdict} ${mix}; ${margin}.`
}

// How the £ impact on an action is worked out (menu_engineering.build_action_list).
export const IMPACT_EXPLAINED =
  'The change in contribution over the chosen period. Plowhorse: its margin brought up to the category average. ' +
  'Puzzle: its sales brought up to the popularity line. Dog: if cut, its customers switch to an average-margin dish.'
