// The steps a new restaurant works through before it has results.
// Prices are optional: benchmarks work until the restaurant has its own.
export function setupSteps(status) {
  return [
    {
      key: 'dishes', label: 'Dishes', done: status.dishes > 0,
      figure: String(status.dishes),
    },
    {
      key: 'recipes', label: 'Recipes', done: status.dishes > 0 && status.dishes_with_recipe === status.dishes,
      figure: `${status.dishes_with_recipe} / ${status.dishes}`,
    },
    {
      key: 'sales', label: 'Sales', done: status.has_sales,
      figure: status.has_sales ? 'Entered' : 'None',
    },
    {
      key: 'prices', label: 'Your prices', optional: true, done: status.ingredients_with_own_price > 0,
      figure: `${status.ingredients_with_own_price} / ${status.ingredients_in_use}`,
      hint: 'Ingredients are costed on benchmark prices until you add your own from invoices.',
    },
  ]
}

export function setupComplete(status) {
  return setupSteps(status).every((s) => s.optional || s.done)
}

// The first required step still to do ('dishes', 'recipes' or 'sales'), or null when setup is complete.
export function firstUnfinished(status) {
  return setupSteps(status).find((s) => !s.optional && !s.done)?.key ?? null
}
