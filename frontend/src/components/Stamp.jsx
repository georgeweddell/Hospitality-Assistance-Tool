import { quadrantTextColor } from '../quadrants'

// A quadrant as a rubber stamp: outlined, uppercase, slightly crooked.
// Used on tickets and the dish page; tables use the smaller QuadrantBadge.
function Stamp({ quadrant, tilt = -3, className = '' }) {
  return (
    <span className={`stamp ${className}`} style={{ color: quadrantTextColor(quadrant), '--tilt': `${tilt}deg` }}>
      {quadrant}
    </span>
  )
}

export default Stamp
