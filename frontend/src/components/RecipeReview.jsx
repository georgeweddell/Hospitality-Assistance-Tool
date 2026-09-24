import { useState, useEffect } from 'react'
import { getJson, postJson } from '../api'

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
    <div className="mt-8 p-4 border border-gray-300 rounded">
      <h2 className="text-xl font-semibold mb-3">Recipe review</h2>

      {error && <p className="text-red-600">Something went wrong: {error}</p>}

      <select
        value={selectedId}
        onChange={event => setSelectedId(event.target.value)}
        className="border border-gray-400 rounded px-2 py-1"
      >
        <option value="">Choose a dish…</option>
        {dishes.map(dish => (
          <option key={dish.id} value={dish.id}>{dish.name}</option>
        ))}
      </select>

      {selectedDish && (
        <p className="mt-3">
          Selected: {selectedDish.name} — £{selectedDish.menu_price.toFixed(2)}
        </p>
      )}

      {selectedDish && (
        <button
          onClick={handleEstimate}
          disabled={estimating}
          className="mt-3 px-3 py-1 bg-blue-600 text-white rounded disabled:bg-gray-400"
        >
          {estimating ? 'Estimating…' : 'Estimate recipe'}
        </button>
      )}
    </div>
  )
}

export default RecipeReview