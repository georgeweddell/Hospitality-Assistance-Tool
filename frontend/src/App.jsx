import { useState, useEffect } from 'react'
import { getJson } from './api'
import useHashRoute from './useHashRoute'
import { presets, rangeQuery } from './dateRange'
import Layout from './components/Layout'
import MenuSummary from './components/MenuSummary'
import ActionList from './components/ActionList'
import QuadrantChart from './components/QuadrantChart'
import MenuPage from './components/MenuPage'
import DishPage from './components/DishPage'
import IngredientsPage from './components/IngredientsPage'
import SalesPage from './components/SalesPage'
import RangePicker from './components/RangePicker'
import { QuadrantLegend } from './components/QuadrantBadge'

const TITLES = {
  overview: 'Overview',
  menu: 'Menu',
  ingredients: 'Ingredients',
  sales: 'Sales',
  analysis: 'Insights',
}

// Pages whose figures depend on the chosen period.
const RANGED_PAGES = ['overview', 'menu', 'sales', 'analysis']

// The chosen period survives a page reload in this tab. Storage can be
// unavailable, so failures just mean starting from the default.
const RANGE_KEY = 'analysis-range'
function loadRange() {
  try {
    return JSON.parse(sessionStorage.getItem(RANGE_KEY))
  } catch {
    return null
  }
}
function saveRange(range) {
  try {
    sessionStorage.setItem(RANGE_KEY, JSON.stringify(range))
  } catch {
    // not important enough to surface
  }
}

function NoSales() {
  return (
    <div className="empty">
      <p className="section-title text-ink">No sales in this period</p>
      <p className="mt-2">
        Choose another period, or <a href="#/sales" className="link">enter sales</a>.
      </p>
    </div>
  )
}

function App() {
  const { page, id } = useHashRoute()
  const [lastSale, setLastSale] = useState(undefined)   // undefined = not loaded yet
  const [range, setRange] = useState(loadRange)
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [refreshKey, setRefreshKey] = useState(0)

  // 1. Find the latest sale, which the default period and presets are based on.
  useEffect(() => {
    let ignore = false
    getJson('/sales/coverage')
      .then((c) => {
        if (ignore) return
        setLastSale(c.last_date)
        setRange((r) => r ?? { key: 'latest-month', ...presets(c.last_date)[0] })
      })
      .catch((err) => { if (!ignore) setError(err.message) })
    return () => { ignore = true }
  }, [refreshKey])

  // 2. Load everything the pages share for the chosen period, in a fixed number
  //    of calls. Bumping refreshKey (e.g. after a dish or sales change) reloads it.
  useEffect(() => {
    if (!range) return
    let ignore = false
    const q = rangeQuery(range)
    Promise.all([
      getJson(`/dishes/classifications?${q}`),
      getJson(`/dishes/action-list?${q}`),
      getJson(`/dishes/incomplete?${q}`),
      getJson('/dishes'),
      getJson(`/sales/coverage?${q}`),
    ])
      .then(([dishes, actions, incomplete, allDishes, coverage]) => {
        if (ignore) return
        setData({ dishes, actions, incomplete, allDishes, coverage, range })
        setError(null)
      })
      .catch((err) => {
        if (!ignore) setError(err.message)
      })
    return () => {
      ignore = true
    }
  }, [range, refreshKey])

  const refresh = () => setRefreshKey((k) => k + 1)
  const changeRange = (r) => {
    setRange(r)
    saveRange(r)
  }

  const hasSales = data?.coverage.days_with_sales.length > 0

  let content
  if (error) {
    content = (
      <div className="alert-error flex flex-wrap items-center justify-between gap-3">
        <span><span className="font-semibold">Couldn't load your menu data.</span> {error}</span>
        <button type="button" onClick={refresh} className="btn btn-secondary btn-sm">Try again</button>
      </div>
    )
  } else if (page === 'ingredients') {
    content = <IngredientsPage onChanged={refresh} />
  } else if (!data) {
    content = (
      <div className="flex items-center gap-3 text-muted">
        <span className="h-4 w-4 animate-spin rounded-full border-2 border-line border-t-accent" aria-hidden="true" />
        Loading menu data…
      </div>
    )
  } else if (page === 'menu' && id) {
    content = (
      <DishPage
        dishId={id}
        range={data.range}
        analysed={data.dishes.find((d) => d.dish_id === id)}
        onChanged={refresh}
      />
    )
  } else if (page === 'menu') {
    content = (
      <MenuPage allDishes={data.allDishes} analysed={data.dishes} incomplete={data.incomplete}
                range={data.range} onChanged={refresh} />
    )
  } else if (page === 'sales') {
    content = <SalesPage range={data.range} coverage={data.coverage} onSaved={refresh} />
  } else if (!hasSales) {
    content = <NoSales />
  } else if (page === 'analysis') {
    const categories = [...new Set(data.dishes.map((d) => d.category))].filter(Boolean)
    content = (
      <div className="space-y-5">
        <QuadrantLegend />
        <div className="grid gap-5 xl:grid-cols-2">
          {categories.map((category) => (
            <QuadrantChart key={category} category={category} dishes={data.dishes} />
          ))}
        </div>
      </div>
    )
  } else {
    content = (
      <div className="space-y-5">
        <MenuSummary dishes={data.dishes} actions={data.actions} />
        <ActionList actions={data.actions} dishes={data.dishes} />
      </div>
    )
  }

  const showPicker = RANGED_PAGES.includes(page) && range && lastSale !== undefined
  const picker = showPicker && (
    <RangePicker range={range} lastSale={lastSale}
                 coverage={data?.range === range ? data.coverage : null} onChange={changeRange} />
  )

  return (
    <Layout
      page={page}
      title={page === 'menu' && id ? null : TITLES[page]}
      toolbar={picker}
      badges={{ menu: data?.incomplete.length }}
    >
      {content}
    </Layout>
  )
}

export default App
