import { quadrantColor, quadrantTextColor } from '../quadrants'

// ▲ / ▼ with the size of a change since the previous period. Rises in green;
// falls stay neutral.
function Delta({ value, format = (v) => `${v}%` }) {
  if (value == null) return null
  const rounded = Math.round(value * 10) / 10
  if (rounded === 0) return <span className="chip chip-muted num">=</span>
  const up = rounded > 0
  return (
    <span className={`chip num ${up ? '' : 'chip-muted'}`}
          style={up ? { color: quadrantTextColor('Star'), backgroundColor: `${quadrantColor('Star')}1f` } : undefined}>
      {up ? '▲' : '▼'} {format(Math.abs(rounded))}
    </span>
  )
}

export default Delta
