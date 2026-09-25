import { quadrantColor, quadrantTextColor } from '../quadrants'

function QuadrantBadge({ quadrant }) {
  const color = quadrantColor(quadrant)
  return (
    <span className="chip" style={{ color: quadrantTextColor(quadrant), backgroundColor: `${color}1f` }}>
      <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: color }} />
      {quadrant}
    </span>
  )
}

export default QuadrantBadge
