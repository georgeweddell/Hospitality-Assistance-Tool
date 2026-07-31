import { useState, useEffect } from 'react'

import {
  ScatterChart, Scatter, XAxis, YAxis, CartesianGrid,
  Tooltip, ReferenceLine, ResponsiveContainer, LabelList
} from 'recharts'

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

export default QuadrantChart