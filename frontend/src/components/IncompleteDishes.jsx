import { useState, useEffect } from 'react'

function IncompleteDishes({ refreshCount }) {
  const [items, setItems] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetch('http://localhost:8000/dishes/incomplete')
      .then((response) => {
        if (!response.ok) {
          throw new Error(`Backend returned ${response.status}`)
        }
        return response.json()
      })
      .then((data) => {
        setItems(data)
        setLoading(false)
      })
      .catch((err) => {
        setError(err.message)
        setLoading(false)
      })
  }, [refreshCount])

  if (error) return <p>Needs attention error: {error}</p>
  if (loading) return <p>Loading outstanding items...</p>
  if (items.length === 0) return null

  return (
    <div className="card wide">
      <h2>Needs attention</h2>
      <table>
        <thead>
          <tr>
            <th>Dish</th>
            <th>Category</th>
            <th>Outstanding</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.dish_id}>
              <td>{item.dish_name}</td>
              <td>{item.category || '—'}</td>
              <td>{item.reasons.join(', ')}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default IncompleteDishes