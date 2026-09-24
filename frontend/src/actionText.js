// Wording for actions, shared by the Overview's move cards and the Actions page.
// Only short labels appear on screen; explanations are shown on demand (Hint).
import { percent, pounds } from './format'

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
