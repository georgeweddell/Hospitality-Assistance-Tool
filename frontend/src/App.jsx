import { useState, useEffect } from 'react'
import { getJson } from './api'
import useHashRoute from './useHashRoute'
import { presets, previousRange, rangeQuery } from './dateRange'
import Layout from './components/Layout'
import OverviewPage from './components/OverviewPage'
import ActionList from './components/ActionList'
import InsightsPage from './components/InsightsPage'
import MenuPage from './components/MenuPage'
import DishPage from './components/DishPage'
import IngredientsPage from './components/IngredientsPage'
import SalesPage from './components/SalesPage'
import ImportsPage from './components/ImportsPage'
import SettingsPage from './components/SettingsPage'
import SetupPage from './components/SetupPage'
import SetupChecklist from './components/SetupChecklist'
import { setupComplete } from './setup'
import RangePicker from './components/RangePicker'
import ReportsPage from './components/ReportsPage'

const TITLES = {
  overview: 'overview',
  actions: 'actions',
  menu: 'menu',
  ingredients: 'ingredients',
  sales: 'sales',
  imports: 'imports',
  analysis: 'insights',
  settings: 'settings',
  setup: 'set up',
  reports: 'reports',
}

// Pages whose figures depend on the chosen period.
const RANGED_PAGES = ['overview', 'actions', 'menu', 'sales', 'analysis']

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
      <a href="#/sales" className="btn btn-secondary mt-4">Enter sales</a>
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
        setRange((r) => {
          const options = presets(c.last_date)
          if (!r) return { key: 'latest-month', ...options[0] }
          // A preset follows the data: after new sales are imported, "Latest month"
          // moves on to the new month. A custom range stays as chosen.
          const preset = options.find((p) => p.key === r.key)
          if (!preset || (preset.from === r.from && preset.to === r.to)) return r
          const moved = { key: r.key, ...preset }
          saveRange(moved)
          return moved
        })
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
      getJson(`/dishes/classifications?${rangeQuery(previousRange(range))}`),   // for "since last period"
      getJson('/setup/status'),
    ])
      .then(([dishes, actions, incomplete, allDishes, coverage, prevDishes, setup]) => {
        if (ignore) return
        setData({ dishes, actions, incomplete, allDishes, coverage, prevDishes, setup, range })
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

  // After starting fresh or loading the demo: forget the chosen period and
  // menu view (they may point at data that's gone) and reload everything.
  const afterReset = () => {
    try {
      sessionStorage.removeItem(RANGE_KEY)
      sessionStorage.removeItem('menu-view')
    } catch {
      // nothing stored
    }
    setRange(null)
    setData(null)
    refresh()
  }
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
    content = <IngredientsPage onChanged={refresh} ownCostShare={data?.setup?.own_cost_share} />
  } else if (page === 'imports') {
    content = <ImportsPage onChanged={refresh} />
  } else if (page === 'settings') {
    content = <SettingsPage onReset={afterReset} onChanged={refresh} />
  } else if (page === 'reports') {
    content = <ReportsPage id={id} range={range} />
  } else if (!data) {
    content = (
      <div className="flex items-center gap-3 text-muted">
        <span className="h-4 w-4 animate-spin rounded-full border-2 border-line border-t-accent" aria-hidden="true" />
        Loading menu data…
      </div>
    )
  } else if (page === 'setup') {
    content = <SetupPage status={data.setup} onChanged={refresh} />
  } else if (page === 'menu' && id) {
    content = (
      <DishPage
        dishId={id}
        range={data.range}
        analysed={data.dishes.find((d) => d.dish_id === id)}
        action={data.actions.find((a) => a.dish_id === id)}
        actionRank={data.actions.findIndex((a) => a.dish_id === id) + 1}
        onChanged={refresh}
      />
    )
  } else if (page === 'menu') {
    content = (
      <MenuPage allDishes={data.allDishes} analysed={data.dishes} incomplete={data.incomplete}
                setup={data.setup} range={data.range} onChanged={refresh} />
    )
  } else if (page === 'sales') {
    content = <SalesPage range={data.range} coverage={data.coverage} onSaved={refresh} />
  } else if (page === 'overview' && data.setup && !setupComplete(data.setup)) {
    // A new restaurant: the checklist first, then any results there already are.
    content = (
      <div className="space-y-6">
        <SetupChecklist status={data.setup} />
        {hasSales && (
          <OverviewPage dishes={data.dishes} prevDishes={data.prevDishes} actions={data.actions}
                        range={data.range} unchecked={data.setup?.unchecked_recipes} />
        )}
      </div>
    )
  } else if (!hasSales) {
    content = <NoSales />
  } else if (page === 'actions') {
    content = <ActionList actions={data.actions} dishes={data.dishes} />
  } else if (page === 'analysis') {
    content = <InsightsPage dishes={data.dishes} prevDishes={data.prevDishes} actions={data.actions} range={data.range} />
  } else {
    content = (
      <OverviewPage dishes={data.dishes} prevDishes={data.prevDishes} actions={data.actions}
                    range={data.range} unchecked={data.setup?.unchecked_recipes} />
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
