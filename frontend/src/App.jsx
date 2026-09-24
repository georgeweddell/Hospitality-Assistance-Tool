import { useState, useEffect } from 'react'
import { getJson } from './api'
import useHashRoute from './useHashRoute'
import Layout from './components/Layout'
import MenuSummary from './components/MenuSummary'
import ActionList from './components/ActionList'
import QuadrantChart from './components/QuadrantChart'
import MenuPage from './components/MenuPage'
import DishPage from './components/DishPage'
import { QuadrantLegend } from './components/QuadrantBadge'

const TITLES = {
  overview: 'Overview',
  menu: 'Menu',
  analysis: 'Insights',
}

function App() {
  const { page, id } = useHashRoute()
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [refreshKey, setRefreshKey] = useState(0)

  // Load everything the dashboard and menu need once, in 4 calls, and share it
  // across pages. Bumping refreshKey (e.g. after a dish changes) reloads it.
  useEffect(() => {
    let ignore = false
    Promise.all([
      getJson('/dishes/classifications'),
      getJson('/dishes/action-list'),
      getJson('/dishes/incomplete'),
      getJson('/dishes'),
    ])
      .then(([dishes, actions, incomplete, allDishes]) => {
        if (ignore) return
        setData({ dishes, actions, incomplete, allDishes })
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

  let content
  if (error) {
    content = (
      <div className="rounded-xl border border-danger/40 bg-surface p-5">
        <p className="font-medium text-danger">Couldn't load your menu data</p>
        <p className="mt-1 text-sm text-muted">{error}</p>
        <button type="button" onClick={refresh} className="mt-3 text-sm font-medium text-accent hover:underline">
          Try again
        </button>
      </div>
    )
  } else if (!data) {
    content = (
      <div className="flex items-center gap-3 text-muted">
        <span className="h-4 w-4 animate-spin rounded-full border-2 border-line border-t-accent" />
        Loading menu data…
      </div>
    )
  } else if (page === 'menu' && id) {
    content = (
      <DishPage
        dishId={id}
        analysed={data.dishes.find((d) => d.dish_id === id)}
        onChanged={refresh}
      />
    )
  } else if (page === 'menu') {
    content = (
      <MenuPage allDishes={data.allDishes} analysed={data.dishes} incomplete={data.incomplete} onChanged={refresh} />
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
  } else {
    content = (
      <div className="space-y-8">
        <MenuSummary dishes={data.dishes} actions={data.actions} excludedCount={data.incomplete.length} />
        <ActionList actions={data.actions} dishes={data.dishes} />
      </div>
    )
  }

  return (
    <Layout page={page} title={page === 'menu' && id ? null : TITLES[page]} badges={{ menu: data?.incomplete.length }}>
      {content}
    </Layout>
  )
}

export default App
