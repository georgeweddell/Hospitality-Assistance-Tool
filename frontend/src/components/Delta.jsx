import { quadrantColor, quadrantTextColor } from '../quadrants'

// ▲ / ▼ with the size of a change since the previous period. Rises in green;
// falls stay neutral. `onTile`: a plain paper pill, for use on a colour tile.
function Delta({ value, format = (v) => `${v}%`, onTile = false }) {
  if (value == null) return null
  const rounded = Math.round(value * 10) / 10
  const paper = onTile ? { color: 'var(--ink)', backgroundColor: 'var(--surface)' } : undefined
  if (rounded === 0) return <span className="chip chip-muted num" style={paper}>=</span>
  const up = rounded > 0
  return (
    <span className={`chip num ${up ? '' : 'chip-muted'}`}
          style={paper ?? (up ? { color: quadrantTextColor('Star'), backgroundColor: `${quadrantColor('Star')}1f` } : undefined)}>
      {up ? '▲' : '▼'} {format(Math.abs(rounded))}
    </span>
  )
}

export default Delta
