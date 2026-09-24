import { useState, useEffect } from 'react'
import { getJson } from './api'
import useHashRoute from './useHashRoute'
import Layout from './components/Layout'
import MenuSummary from './components/MenuSummary'
import ActionList from './components/ActionList'
import QuadrantChart from './components/QuadrantChart'
import DishTable from './components/DishTable'
import IncompleteDishes from './components/IncompleteDishes'
import AddDishForm from './components/AddDishForm'
import RecipeReview from './components/RecipeReview'
import { QuadrantLegend } from './components/QuadrantBadge'

const TITLES = {
  overview: 'Overview',
  analysis: 'Menu analysis',
  dishes: 'Dishes',
  setup: 'Menu setup',
}

function App() {
  const page = useHashRoute()
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [refreshKey, setRefreshKey] = useState(0)

  // Load everything the dashboard needs once, in 3 calls, and share it across
  // pages. Bumping refreshKey (e.g. after adding a dish) reloads it.
  useEffect(() => {
    let ignore = false
    Promise.all([
      getJson('/dishes/classifications'),
      getJson('/dishes/action-list'),
      getJson('/dishes/incomplete'),
    ])
      .then(([dishes, actions, incomplete]) => {
        if (ignore) return
        setData({ dishes, actions, incomplete })
        setError(null)
      })
      .catch((err) => {
        if (!ignore) setError(err.message)
      })
    return () => {
      ignore = true
    }
  }, [refreshKey])

  const refresh = () => setRefreshKey((k) => k + 1)

  const needsData = page !== 'setup'
  let content
  if (needsData && error) {
    content = (
      <div className="rounded-xl border border-danger/40 bg-surface p-5">
        <p className="font-medium text-danger">Couldn't load your menu data</p>
        <p className="mt-1 text-sm text-muted">{error}</p>
        <button type="button" onClick={refresh} className="mt-3 text-sm font-medium text-accent hover:underline">
          Try again
        </button>
      </div>
    )
  } else if (needsData && !data) {
    content = (
      <div className="flex items-center gap-3 text-muted">
        <span className="h-4 w-4 animate-spin rounded-full border-2 border-line border-t-accent" />
        Loading menu data…
      </div>
    )
  } else if (page === 'overview') {
    content = (
      <div className="space-y-8">
        <MenuSummary dishes={data.dishes} actions={data.actions} excludedCount={data.incomplete.length} />
        <ActionList actions={data.actions} dishes={data.dishes} />
      </div>
    )
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
  } else if (page === 'dishes') {
    content = (
      <div className="space-y-6">
        <DishTable dishes={data.dishes} />
        <IncompleteDishes items={data.incomplete} />
      </div>
    )
  } else {
    content = (
      <div className="grid items-start gap-5 lg:grid-cols-2">
        <AddDishForm onDishAdded={refresh} />
        {/* key remounts it after a dish is added, so the new dish appears in its dropdown */}
        <RecipeReview key={refreshKey} />
      </div>
    )
  }

  return (
    <Layout page={page} title={TITLES[page]} badges={{ dishes: data?.incomplete.length }}>
      {content}
    </Layout>
  )
}

export default App
