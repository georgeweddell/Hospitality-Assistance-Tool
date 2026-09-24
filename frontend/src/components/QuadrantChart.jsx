import {
  ScatterChart, Scatter, XAxis, YAxis, CartesianGrid,
  Tooltip, ReferenceLine, ResponsiveContainer, LabelList, Cell
} from 'recharts'
import Card from './Card'
import QuadrantBadge from './QuadrantBadge'
import { quadrantColor } from '../quadrants'

function QuadrantChart({ dishes, category }) {
  const inCategory = dishes.filter((d) => d.category === category)
  const popLine = inCategory[0].popularity_threshold
  const profLine = inCategory[0].profitability_threshold

  return (
    <Card title={category} aside={`${popLine.toFixed(1)}% mix · £${profLine.toFixed(2)} margin`}>
      <div className="chart">
        <ResponsiveContainer width="100%" height={300}>
          <ScatterChart margin={{ top: 30, right: 20, bottom: 30, left: 10 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              type="number"
              dataKey="menu_mix_percent"
              name="Menu mix"
              unit="%"
              label={{ value: 'Popularity (menu mix %)', position: 'bottom', offset: 10 }}
            />
            <YAxis
              type="number"
              dataKey="margin_pounds"
              name="Margin"
              tickFormatter={(v) => `£${v}`}
              label={{ value: 'Margin (£)', angle: -90, position: 'insideLeft', offset: 5 }}
            />
            <Tooltip content={<DishTooltip />} cursor={false} />
            <ReferenceLine x={popLine} strokeDasharray="4 4" />
            <ReferenceLine y={profLine} strokeDasharray="4 4" />
            <Scatter data={inCategory}>
              {inCategory.map((dish) => (
                <Cell key={dish.dish_id} fill={quadrantColor(dish.quadrant)} />
              ))}
              <LabelList dataKey="dish_name" position="top" />
            </Scatter>
          </ScatterChart>
        </ResponsiveContainer>
      </div>
    </Card>
  )
}

function DishTooltip({ active, payload }) {
  if (!active || !payload || payload.length === 0) return null

  const dish = payload[0].payload

  return (
    <div className="rounded-lg border border-line bg-surface px-3 py-2 text-sm text-ink shadow-md">
      <div className="mb-1 flex items-center gap-2">
        <strong>{dish.dish_name}</strong>
        <QuadrantBadge quadrant={dish.quadrant} />
      </div>
      <div className="tabular-nums text-muted">
        <div>Margin: £{dish.margin_pounds.toFixed(2)}</div>
        <div>Menu mix: {dish.menu_mix_percent.toFixed(2)}%</div>
        <div>Units sold: {dish.units_sold}</div>
      </div>
    </div>
  )
}

export default QuadrantChart
