// One colour per quadrant, shared by the charts, badges and summary so a Dog
// is the same red everywhere. `action` is the short label for the summary cards.
export const QUADRANTS = {
  Star: { color: '#22a05a', action: 'Keep and feature' },
  Plowhorse: { color: '#d98a0b', action: 'Reprice or re-engineer' },
  Puzzle: { color: '#3b82f6', action: 'Promote' },
  Dog: { color: '#e0525a', action: 'Review for removal' },
}

export const QUADRANT_ORDER = ['Star', 'Plowhorse', 'Puzzle', 'Dog']

export function quadrantColor(quadrant) {
  return QUADRANTS[quadrant]?.color ?? '#888888'
}
