import { useState, useEffect } from 'react'

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

export default DishCard