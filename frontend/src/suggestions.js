import { useEffect, useState } from 'react'
import { getJson } from './api'
import { rangeQuery } from './dateRange'

// The business checks for a period (backend: suggestions.py): every check, the
// ones that fire first, each with its figures and the rule of thumb it was
// judged against. `reload` changes whenever the data does.
export function useSuggestions(range, reload) {
  const [checks, setChecks] = useState(null)
  useEffect(() => {
    let ignore = false
    getJson(`/suggestions?${rangeQuery(range)}`)
      .then((rows) => { if (!ignore) setChecks(rows) })
      .catch(() => { if (!ignore) setChecks([]) })
    return () => { ignore = true }
  }, [range, reload])
  return checks
}
