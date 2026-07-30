import { useState, useEffect } from 'react'

import {
  ScatterChart, Scatter, XAxis, YAxis, CartesianGrid,
  Tooltip, ReferenceLine, ResponsiveContainer, LabelList
} from 'recharts'

function App() {
  const [dishes, setDishes] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetch('http://localhost:8000/dishes/classifications')
      .then((response) => {
        if (!response.ok) {
          throw new Error(`Backend returned ${response.status}`)
        }
        return response.json()
      })
      .then((data) => {
        setDishes(data)
        setLoading(false)
      })
      .catch((err) => {
        setError(err.message)
        setLoading(false)
      })
  }, [])

  if (error) return <p>Error: {error}</p>
  if (loading) return <p>Loading...</p>

  const categories = [...new Set(dishes.map((d) => d.category))].filter(Boolean)

  return (
    <div>
      <h1>Menu & Margin Engine</h1>
      {categories.map((category) => (
        <QuadrantChart key={category} category={category} dishes={dishes} />
      ))}
      <ActionList />
      {dishes.map((dish) => (
        <DishCard key={dish.dish_id} dish={dish} />
      ))}
    </div>
  )
}

function ActionList() {
  const [items, setItems] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetch('http://localhost:8000/dishes/action-list')
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
  }, [])

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

function DishCard({ dish }) {
  return (
    <div className="card dish-card">
      <h2>{dish.dish_name}</h2>
      <p>Category: {dish.category}</p>
      <p>Quadrant: {dish.quadrant}</p>
      <p>Menu Price: £{dish.menu_price.toFixed(2)}</p>
      <p>Plate Cost: £{dish.plate_cost.toFixed(2)}</p>
      <p>Margin: £{dish.margin_pounds.toFixed(2)} ({dish.margin_percent.toFixed(2)}%)</p>
      <p>Units Sold: {dish.units_sold} (Menu Mix: {dish.menu_mix_percent.toFixed(2)}%)</p>
      {dish.skipped_ingredients.length > 0 && (
      <p className="warning">
        ⚠ Not costed: {dish.skipped_ingredients.join(', ')}
      </p>
)}
    </div>
  )
}

function QuadrantChart({ dishes, category }) {
  const inCategory = dishes.filter((d) => d.category === category)
  const popLine = inCategory[0].popularity_threshold
  const profLine = inCategory[0].profitability_threshold

  return (
    <div className="card wide">
      <h2>{category}</h2>
      <ResponsiveContainer width="100%" height={350}>
        <ScatterChart margin={{ top: 20, right: 30, bottom: 40, left: 20 }}>
          <CartesianGrid stroke="#333" />
          <XAxis
            type="number"
            dataKey="menu_mix_percent"
            name="Menu mix"
            unit="%"
            label={{ value: 'Popularity (menu mix %)', position: 'bottom' }}
          />
          <YAxis
            type="number"
            dataKey="margin_pounds"
            name="Margin"
            label={{ value: 'Margin (£)', angle: -90, position: 'left' }}
          />
          <Tooltip content={<DishTooltip />} cursor={false} />
          <ReferenceLine x={popLine} stroke="#e06c75" />
          <ReferenceLine y={profLine} stroke="#e06c75" />
          <Scatter data={inCategory} fill="#61afef">
            <LabelList dataKey="dish_name" position="top" fontSize={11}/>
          </Scatter>
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  )
}

function DishTooltip({ active, payload }) {
  if (!active || !payload || payload.length === 0) return null

  const dish = payload[0].payload

  return (
    <div className="tooltip">
      <strong>{dish.dish_name}</strong> — {dish.quadrant}
      <div>Margin: £{dish.margin_pounds.toFixed(2)}</div>
      <div>Menu mix: {dish.menu_mix_percent.toFixed(2)}%</div>
      <div>Units sold: {dish.units_sold}</div>
    </div>
  )
}

export default App