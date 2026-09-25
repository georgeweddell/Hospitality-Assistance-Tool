// The steps a new restaurant works through before it has results, in order.
// Prices come before recipes (invoice ingredients are then there to use), and
// are optional: benchmarks work until the restaurant has its own.
export function setupSteps(status) {
  return [
    {
      key: 'dishes', label: 'Dishes', done: status.dishes > 0,
      figure: String(status.dishes),
    },
    {
      key: 'prices', label: 'Your prices', optional: true, done: status.ingredients_with_own_price > 0,
      figure: `${status.ingredients_with_own_price} / ${status.ingredients_in_use}`,
      hint: 'Ingredients are costed on benchmark prices until you add your own from invoices.',
    },
    {
      key: 'recipes', label: 'Recipes', done: status.dishes > 0 && status.dishes_with_recipe === status.dishes,
      figure: `${status.dishes_with_recipe} / ${status.dishes}`,
    },
    {
      key: 'sales', label: 'Sales', done: status.has_sales,
      figure: status.has_sales ? 'Entered' : 'None',
    },
  ]
}

export function setupComplete(status) {
  return setupSteps(status).every((s) => s.optional || s.done)
}

// Where Continue setup opens: the first step still to do, or null when setup
// is complete. The optional prices step only counts before any recipes exist
// (after that, the owner has chosen to go on without it).
export function firstUnfinished(status) {
  const pricesPending = status.dishes_with_recipe === 0
  return setupSteps(status).find((s) => !s.done && (!s.optional || pricesPending))?.key ?? null
}
