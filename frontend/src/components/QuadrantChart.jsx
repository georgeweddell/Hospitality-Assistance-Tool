import { useState } from 'react'
import {
  ScatterChart, Scatter, XAxis, YAxis, CartesianGrid,
  Tooltip, ReferenceLine, ReferenceArea, ResponsiveContainer, LabelList, Cell
} from 'recharts'
import Card from './Card'
import Hint from './Hint'
import QuadrantBadge from './QuadrantBadge'
import { quadrantColor, quadrantTextColor } from '../quadrants'
import { percent, pounds } from '../format'
import { placeLabels } from '../labelPlacement'
import { navigate } from '../useHashRoute'

// Chart geometry, shared by the chart and the label placement.
const HEIGHT = 340
const MARGIN = { top: 8, right: 16, bottom: 24, left: 0 }
const Y_AXIS_WIDTH = 52
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

const signedPounds = (v) => (v > 0 ? `+£${v}` : v < 0 ? `−£${-v}` : '£0')

// Where each dish goes, and where the lines are.
//
// One category: popularity (share of the category's sales) against margin (£),
// with that category's two lines.
//
// All categories: each category is judged against its own lines, so dishes from
// different categories can't share one pair of real lines. Instead each dish is
// placed relative to ITS category's lines: across, its share as a % of the
// popularity line (100% = on the line); up, its margin above or below its
// category's average (£0 = on the line). One pair of lines is then right for
// every dish, and each dot's colour matches the zone it sits in.
function layout(shown, category) {
  if (category) {
    const popLine = shown[0].popularity_threshold
    const profLine = shown[0].profitability_threshold
    const points = shown.map((d) => ({ ...d, x: d.menu_mix_percent, y: d.margin_pounds }))
    const xMax = up(Math.max(...points.map((p) => p.x), popLine) * 1.1, 5)
    return {
      points, xLine: popLine, yLine: profLine, xMax, xStep: xMax <= 20 ? 5 : 10,
      yMin: Math.max(0, down(Math.min(...points.map((p) => p.y), profLine) - 0.25, 0.5)),
      yMax: up(Math.max(...points.map((p) => p.y), profLine) + 0.25, 0.5),
      xFormat: (v) => `${v}%`, yFormat: (v) => `£${v}`,
      xLabel: `Share of ${category.toLowerCase()}s sold`,
      hint: `The dashed lines. Popular: at least ${percent(popLine)} of ${category.toLowerCase()} sales (70% of an equal share). Profitable: at least ${pounds(profLine)} margin (the sales-weighted average).`,
    }
  }
  const points = shown.map((d) => ({
    ...d,
    x: (d.menu_mix_percent / d.popularity_threshold) * 100,
    y: d.margin_pounds - d.profitability_threshold,
  }))
  const xPeak = Math.max(...points.map((p) => p.x), 100) * 1.1
  const xStep = xPeak <= 200 ? 50 : xPeak <= 500 ? 100 : 200
  return {
    points, xLine: 100, yLine: 0, xMax: up(xPeak, xStep), xStep,
    yMin: down(Math.min(...points.map((p) => p.y), 0) - 0.25, 0.5),
    yMax: up(Math.max(...points.map((p) => p.y), 0) + 0.25, 0.5),
    xFormat: (v) => `${v}%`, yFormat: signedPounds,
    xLabel: "Popularity against its category's line",
    hint: "Each category is judged against its own lines, so every dish is placed against its category's: across, its share of its category's sales as a % of the popularity line (100% is on the line); up, its margin above or below its category's average. Pick a category to see real shares and margins.",
  }
}

// Dishes plotted by popularity against margin, with the four quadrants shaded
// and named. `category` null shows every category (see layout). Only the
// dishes in `labelled` (a Set of dish ids) are named on the chart, so names
// don't pile up; every dish shows on hover, and a click opens it.
function QuadrantChart({ dishes, category = null, labelled = new Set() }) {
  const [width, setWidth] = useState(520)
  const shown = category ? dishes.filter((d) => d.category === category) : dishes
  const { points, xLine, yLine, xMax, xStep, yMin, yMax, xFormat, yFormat, xLabel, hint } = layout(shown, category)

  const yStep = yMax - yMin > 8 ? 2 : 1
  const yTicks = []
  for (let t = Math.ceil(yMin / yStep) * yStep; t <= yMax; t += yStep) yTicks.push(t)
  const xTicks = []
  for (let t = 0; t <= xMax; t += xStep) xTicks.push(t)

  const placement = placeLabels(
    points.filter((p) => labelled.has(p.dish_id)).map((p) => ({ key: p.dish_id, x: p.x, y: p.y, text: p.dish_name })),
    {
      xDomain: [0, xMax],
      yDomain: [yMin, yMax],
      width: width - MARGIN.left - MARGIN.right - Y_AXIS_WIDTH,
      height: HEIGHT - MARGIN.top - MARGIN.bottom - X_AXIS_HEIGHT,
      corners: { topLeft: 'PUZZLES', topRight: 'STARS', bottomLeft: 'DOGS', bottomRight: 'PLOWHORSES' },
    },
  )

  // Draws each named dish on one line at its placed position around the dot.
  const renderLabel = ({ x, y, width: w, height: h, index }) => {
    const dish = points[index]
    const p = dish && placement[dish.dish_id]
    if (!p) return null   // not one of the named dishes (shown on hover instead)
    return (
      <text x={x + w / 2 + p.dx} y={y + h / 2 + p.dy} textAnchor={p.anchor}
            fill="var(--ink)" fontSize={12} fontWeight={500}>
        {dish.dish_name}
      </text>
    )
  }

  return (
    <Card
      title={category ? `${category}s` : 'All dishes'}
      aside={
        <span className="inline-flex items-center gap-2">
          <span className="num">{shown.length} dishes</span>
          <Hint align="right" label="Where the lines are" content={hint} />
        </span>
      }
    >
      <div className="chart">
        <ResponsiveContainer width="100%" height={HEIGHT} onResize={(w) => setWidth(w)}>
          <ScatterChart margin={MARGIN}>
            <ReferenceArea x1={0} x2={xLine} y1={yLine} y2={yMax} fill={quadrantColor('Puzzle')}
                           fillOpacity={0.07} stroke="none" label={zoneLabel('PUZZLES', 'Puzzle', 'insideTopLeft')} />
            <ReferenceArea x1={xLine} x2={xMax} y1={yLine} y2={yMax} fill={quadrantColor('Star')}
                           fillOpacity={0.07} stroke="none" label={zoneLabel('STARS', 'Star', 'insideTopRight')} />
            <ReferenceArea x1={0} x2={xLine} y1={yMin} y2={yLine} fill={quadrantColor('Dog')}
                           fillOpacity={0.07} stroke="none" label={zoneLabel('DOGS', 'Dog', 'insideBottomLeft')} />
            <ReferenceArea x1={xLine} x2={xMax} y1={yMin} y2={yLine} fill={quadrantColor('Plowhorse')}
                           fillOpacity={0.07} stroke="none" label={zoneLabel('PLOWHORSES', 'Plowhorse', 'insideBottomRight')} />
            <CartesianGrid vertical={false} />
            <XAxis type="number" dataKey="x" domain={[0, xMax]} ticks={xTicks} tickFormatter={xFormat}
                   height={X_AXIS_HEIGHT} label={{ value: xLabel, position: 'bottom', offset: 6 }} />
            <YAxis type="number" dataKey="y" domain={[yMin, yMax]} ticks={yTicks} tickFormatter={yFormat}
                   width={Y_AXIS_WIDTH} />
            <Tooltip content={<DishTooltip />} cursor={false} />
            <ReferenceLine x={xLine} strokeDasharray="4 4" />
            <ReferenceLine y={yLine} strokeDasharray="4 4" />
            <Scatter data={points} isAnimationActive={false} cursor="pointer"
                     onClick={(point) => navigate(`menu/${point.dish_id ?? point.payload?.dish_id}`)}>
              {points.map((dish) => (
                <Cell key={dish.dish_id} fill={quadrantColor(dish.quadrant)} stroke="var(--surface)" strokeWidth={2} />
              ))}
              <LabelList dataKey="dish_name" content={renderLabel} />
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
    <div className="card px-3 py-2.5 text-sm shadow-md">
      <div className="mb-1.5 flex items-center gap-2">
        <strong>{dish.dish_name}</strong>
        <QuadrantBadge quadrant={dish.quadrant} />
      </div>
      <dl className="num grid grid-cols-[auto_auto] gap-x-4 gap-y-0.5">
        <dt className="text-muted">Category</dt><dd className="text-right">{dish.category}</dd>
        <dt className="text-muted">Margin</dt><dd className="text-right">{pounds(dish.margin_pounds)}</dd>
        <dt className="text-muted">Share of {dish.category?.toLowerCase()}s</dt><dd className="text-right">{percent(dish.menu_mix_percent)}</dd>
        <dt className="text-muted">Units sold</dt><dd className="text-right">{dish.units_sold}</dd>
      </dl>
    </div>
  )
}

export default QuadrantChart
