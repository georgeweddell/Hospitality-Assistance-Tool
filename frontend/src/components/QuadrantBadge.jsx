import { QUADRANT_ORDER, quadrantColor } from '../quadrants'

function QuadrantBadge({ quadrant }) {
  const color = quadrantColor(quadrant)
  return (
    <span
      className="inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-medium"
      style={{ color, backgroundColor: `${color}1f` }}
    >
      <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: color }} />
      {quadrant}
    </span>
  )
}

export function QuadrantLegend() {
  return (
    <ul className="flex flex-wrap gap-x-5 gap-y-2 text-sm">
      {QUADRANT_ORDER.map((name) => (
        <li key={name} className="flex items-center gap-2">
          <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: quadrantColor(name) }} />
          {name}
        </li>
      ))}
    </ul>
  )
}

export default QuadrantBadge
