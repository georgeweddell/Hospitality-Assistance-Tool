import { useEffect, useState } from 'react'
import { getJson } from './api'
import { rangeQuery } from './dateRange'
import { priceForDisplay } from './format'

// Ingredient price changes (backend: price_changes.py): from the start of the
// period to today, for ingredients in current recipes. Rises of 5% or more are
// alerts (is_alert); a change dated after the period says so (after_period).

// Loads the changes for a period (none given: the latest month). `reload` changes whenever the data does.
export function usePriceChanges(range, reload) {
  const [changes, setChanges] = useState(null)
  useEffect(() => {
    let ignore = false
    getJson(`/price-changes${range ? `?${rangeQuery(range)}` : ''}`)
      .then((rows) => { if (!ignore) setChanges(rows) })
      .catch(() => { if (!ignore) setChanges([]) })   // an extra, not worth blocking the page for
    return () => { ignore = true }
  }, [range, reload])
  return changes
}

// "£7.40 → £8.20/kg"
export const priceMove = (c) =>
  `${priceForDisplay(c.old_price, c.unit).replace(/\/(kg|l)$|\s+each$/, '')} → ${priceForDisplay(c.new_price, c.unit)}`

// "+10.8%" / "−4.0%"
export const percentMove = (c) => `${c.change_percent > 0 ? '+' : '−'}${Math.abs(c.change_percent).toFixed(1)}%`
