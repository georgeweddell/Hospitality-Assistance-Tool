import { useState, useEffect } from 'react'
import ActionList from './components/ActionList'
import DishCard from './components/DishCard'
import QuadrantChart from './components/QuadrantChart'
import AddDishForm from './components/AddDishForm'
import IncompleteDishes from './components/IncompleteDishes'
import { getJson } from './api'

function App() {
  const [dishes, setDishes] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [refreshCount, setRefreshCount] = useState(0)

  const loadDishes = () => {
    setRefreshCount((c) => c + 1)
    getJson('/dishes/classifications')
      .then((data) => {
        setDishes(data)
        setLoading(false)
      })
      .catch((err) => {
        setError(err.message)
        setLoading(false)
      })
  }

  useEffect(() => {
    loadDishes()
  }, [])

  if (error) return <p>Error: {error}</p>
  if (loading) return <p>Loading...</p>

  const categories = [...new Set(dishes.map((d) => d.category))].filter(Boolean)

  return (
    <div>
      <h1>Menu & Margin Engine</h1>
      <AddDishForm onDishAdded={loadDishes} />
      {categories.map((category) => (
        <QuadrantChart key={category} category={category} dishes={dishes} />
      ))}
      <ActionList refreshCount={refreshCount} />
      {dishes.map((dish) => (
        <DishCard key={dish.dish_id} dish={dish} />
      ))}
      <IncompleteDishes refreshCount={refreshCount} />
    </div>
  )
}


export default App