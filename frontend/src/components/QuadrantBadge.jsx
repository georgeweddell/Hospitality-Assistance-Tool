import { QUADRANT_ORDER, quadrantColor, quadrantTextColor } from '../quadrants'

function QuadrantBadge({ quadrant }) {
  const color = quadrantColor(quadrant)
  return (
    <span className="chip" style={{ color: quadrantTextColor(quadrant), backgroundColor: `${color}1f` }}>
      <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: color }} />
      {quadrant}
    </span>
  )
}

export function QuadrantLegend() {
  return (
    <ul className="flex flex-wrap gap-x-5 gap-y-2 text-sm">
      {QUADRANT_ORDER.map((name) => (
        <li key={name} className="flex items-center gap-2 font-medium">
          <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: quadrantColor(name) }} />
          {name}s
        </li>
      ))}
    </ul>
  )
}

export default QuadrantBadge
