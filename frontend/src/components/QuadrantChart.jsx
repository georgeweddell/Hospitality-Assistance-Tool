import { useState } from 'react'
import {
  ScatterChart, Scatter, XAxis, YAxis, CartesianGrid,
  Tooltip, ReferenceLine, ReferenceArea, ResponsiveContainer, LabelList, Cell
} from 'recharts'
import Card from './Card'
import QuadrantBadge from './QuadrantBadge'
import { quadrantColor, quadrantTextColor } from '../quadrants'
import { percent, pounds } from '../format'
import { placeLabels } from '../labelPlacement'

// Chart geometry, shared by the chart and the label placement.
const HEIGHT = 340
const MARGIN = { top: 8, right: 16, bottom: 24, left: 0 }
const Y_AXIS_WIDTH = 44
const X_AXIS_HEIGHT = 30

// Round up/down to a tidy axis step.
const up = (v, step) => Math.ceil(v / step) * step
const down = (v, step) => Math.floor(v / step) * step

function zoneLabel(text, quadrant, position) {
  return {
    value: text,
    position,
    offset: 10,
    fill: quadrantTextColor(quadrant),
    fontSize: 11,
    fontWeight: 700,
    letterSpacing: '0.06em',
  }
}

// One category's dishes plotted by popularity (menu mix) against margin, with
// the four quadrants shaded and named so each dish's position reads at a glance.
function QuadrantChart({ dishes, category }) {
  const [width, setWidth] = useState(520)
  const inCategory = dishes.filter((d) => d.category === category)
  const popLine = inCategory[0].popularity_threshold
  const profLine = inCategory[0].profitability_threshold

  const mixes = inCategory.map((d) => d.menu_mix_percent)
  const margins = inCategory.map((d) => d.margin_pounds)
  const xMax = up(Math.max(...mixes, popLine) * 1.1, 5)
  const yMin = Math.max(0, down(Math.min(...margins, profLine) - 0.25, 0.5))
  const yMax = up(Math.max(...margins, profLine) + 0.25, 0.5)
  const yTicks = []
  for (let t = Math.ceil(yMin); t <= yMax; t += 1) yTicks.push(t)
  const xStep = xMax <= 20 ? 5 : 10
  const xTicks = []
  for (let t = 0; t <= xMax; t += xStep) xTicks.push(t)

  const placement = placeLabels(
    inCategory.map((d) => ({ key: d.dish_id, x: d.menu_mix_percent, y: d.margin_pounds, text: d.dish_name })),
    {
      xDomain: [0, xMax],
      yDomain: [yMin, yMax],
      width: width - MARGIN.left - MARGIN.right - Y_AXIS_WIDTH,
      height: HEIGHT - MARGIN.top - MARGIN.bottom - X_AXIS_HEIGHT,
      corners: { topLeft: 'PUZZLES', topRight: 'STARS', bottomLeft: 'DOGS', bottomRight: 'PLOWHORSES' },
    },
  )

  // Draws each name on one line at its placed position around the dot.
  const renderLabel = ({ x, y, width: w, height: h, index }) => {
    const dish = inCategory[index]
    const p = placement[dish.dish_id]
    return (
      <text x={x + w / 2 + p.dx} y={y + h / 2 + p.dy} textAnchor={p.anchor}
            fill="var(--ink)" fontSize={12} fontWeight={500}>
        {dish.dish_name}
      </text>
    )
  }

  return (
    <Card title={category} aside={<span className="num">{inCategory.length} dishes</span>}>
      <div className="chart">
        <ResponsiveContainer width="100%" height={HEIGHT} onResize={(w) => setWidth(w)}>
          <ScatterChart margin={MARGIN}>
            <ReferenceArea x1={0} x2={popLine} y1={profLine} y2={yMax} fill={quadrantColor('Puzzle')}
                           fillOpacity={0.07} stroke="none" label={zoneLabel('PUZZLES', 'Puzzle', 'insideTopLeft')} />
            <ReferenceArea x1={popLine} x2={xMax} y1={profLine} y2={yMax} fill={quadrantColor('Star')}
                           fillOpacity={0.07} stroke="none" label={zoneLabel('STARS', 'Star', 'insideTopRight')} />
            <ReferenceArea x1={0} x2={popLine} y1={yMin} y2={profLine} fill={quadrantColor('Dog')}
                           fillOpacity={0.07} stroke="none" label={zoneLabel('DOGS', 'Dog', 'insideBottomLeft')} />
            <ReferenceArea x1={popLine} x2={xMax} y1={yMin} y2={profLine} fill={quadrantColor('Plowhorse')}
                           fillOpacity={0.07} stroke="none" label={zoneLabel('PLOWHORSES', 'Plowhorse', 'insideBottomRight')} />
            <CartesianGrid vertical={false} />
            <XAxis
              type="number"
              dataKey="menu_mix_percent"
              domain={[0, xMax]}
              ticks={xTicks}
              tickFormatter={(v) => `${v}%`}
              height={X_AXIS_HEIGHT}
              label={{ value: `Share of ${category.toLowerCase()}s sold`, position: 'bottom', offset: 6 }}
            />
            <YAxis
              type="number"
              dataKey="margin_pounds"
              domain={[yMin, yMax]}
              ticks={yTicks}
              tickFormatter={(v) => `£${v}`}
              width={Y_AXIS_WIDTH}
            />
            <Tooltip content={<DishTooltip />} cursor={false} />
            <ReferenceLine x={popLine} strokeDasharray="4 4" />
            <ReferenceLine y={profLine} strokeDasharray="4 4" />
            <Scatter data={inCategory} isAnimationActive={false}>
              {inCategory.map((dish) => (
                <Cell key={dish.dish_id} fill={quadrantColor(dish.quadrant)} stroke="var(--surface)" strokeWidth={2} />
              ))}
              <LabelList dataKey="dish_name" content={renderLabel} />
            </Scatter>
          </ScatterChart>
        </ResponsiveContainer>
      </div>
      <p className="num mt-1 text-sm text-muted">
        Popular from {percent(popLine)} of sales · profitable from {pounds(profLine)} margin
      </p>
    </Card>
  )
}

function DishTooltip({ active, payload }) {
  if (!active || !payload || payload.length === 0) return null
  const dish = payload[0].payload

  return (
    <div className="card px-3 py-2.5 text-sm shadow-md">
      <div className="mb-1.5 flex items-center gap-2">
        <strong>{dish.dish_name}</strong>
        <QuadrantBadge quadrant={dish.quadrant} />
      </div>
      <dl className="num grid grid-cols-[auto_auto] gap-x-4 gap-y-0.5">
        <dt className="text-muted">Margin</dt><dd className="text-right">{pounds(dish.margin_pounds)}</dd>
        <dt className="text-muted">Share of sales</dt><dd className="text-right">{percent(dish.menu_mix_percent)}</dd>
        <dt className="text-muted">Units sold</dt><dd className="text-right">{dish.units_sold}</dd>
      </dl>
    </div>
  )
}

export default QuadrantChart
