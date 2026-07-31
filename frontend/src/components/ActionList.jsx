import { useState, useEffect } from 'react'
import { getJson } from '../api'

function ActionList({ refreshCount }) {
  const [items, setItems] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

useEffect(() => {
    getJson('/dishes/action-list')
      .then((data) => {
        setItems(data)
        setLoading(false)
      })
      .catch((err) => {
        setError(err.message)
        setLoading(false)
      })
  }, [refreshCount])

  if (error) return <p>Action list error: {error}</p>
  if (loading) return <p>Loading actions...</p>

  return (
    <div className="card wide">
      <h2>Action List</h2>
      <table>
        <thead>
          <tr>
            <th>Dish</th>
            <th>Quadrant</th>
            <th>Action</th>
            <th>Impact</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.dish_id}>
              <td>{item.dish_name}</td>
              <td>{item.quadrant}</td>
              <td>{item.action}</td>
              <td>£{item.impact_pounds.toFixed(2)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default ActionList