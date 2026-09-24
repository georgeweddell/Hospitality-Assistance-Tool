import { useState, useEffect } from 'react'
import { getJson, postJson } from '../api'
import Card from './Card'

function RecipeReview() {
  const [dishes, setDishes] = useState([])
  const [selectedId, setSelectedId] = useState("")
  const [error, setError] = useState(null)
  const [rows, setRows] = useState([])
  const [estimating, setEstimating] = useState(false)

  useEffect(() => {
    getJson('/dishes')
      .then(data => setDishes(data))
      .catch(err => setError(err.message))
  }, [])

  const selectedDish = dishes.find(dish => dish.id === Number(selectedId))

  const handleEstimate = () => {
    setEstimating(true)
    setError(null)
    postJson(`/dishes/${selectedId}/estimate-recipe`, {})
      .then(data => setRows(data))
      .catch(err => setError(err.message))
      .finally(() => setEstimating(false))
  }

  return (
    <Card title="Recipe review">
      {error && <p className="mb-3 text-sm text-danger">Something went wrong: {error}</p>}

      <select
        value={selectedId}
        onChange={event => setSelectedId(event.target.value)}
        className="w-full rounded-lg border border-line bg-surface px-3 py-2 text-ink focus:border-accent focus:outline-none"
      >
        <option value="">Choose a dish…</option>
        {dishes.map(dish => (
          <option key={dish.id} value={dish.id}>{dish.name}</option>
        ))}
      </select>

      {selectedDish && (
        <p className="mt-3 text-sm text-muted">
          Selected: {selectedDish.name} — £{selectedDish.menu_price.toFixed(2)}
        </p>
      )}

      {selectedDish && (
        <button
          onClick={handleEstimate}
          disabled={estimating}
          className="mt-3 rounded-lg bg-accent px-4 py-2 font-medium text-accent-ink hover:opacity-90 disabled:opacity-50"
        >
          {estimating ? 'Estimating…' : 'Estimate recipe'}
        </button>
      )}
    </Card>
  )
}

export default RecipeReview