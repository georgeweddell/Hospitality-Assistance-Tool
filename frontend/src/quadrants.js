// One colour per quadrant, shared by the charts, badges and summary, so a Dog
// is the same aubergine everywhere. `text` is a darker shade of the same colour
// for small text on a tinted background (it keeps 4.5:1 contrast); `tint` is the
// light fill for that quadrant's zone or tile.
// `action` is the short label for the Overview's opportunity cards.
export const QUADRANTS = {
  Star: { color: '#2e5a36', text: '#2e5a36', tint: '#d6e5d3', action: 'Keep and feature', meaning: 'Popular and profitable' },
  Plowhorse: { color: '#d9a21e', text: '#7a5600', tint: '#f3e1b0', action: 'Reprice or re-engineer', meaning: 'Popular, low margin' },
  Puzzle: { color: '#2b4c9b', text: '#2b4c9b', tint: '#dce3f2', action: 'Promote', meaning: 'Profitable, rarely ordered' },
  Dog: { color: '#6a2e57', text: '#6a2e57', tint: '#eadae4', action: 'Review for removal', meaning: 'Low margin, few sales' },
}

export const QUADRANT_ORDER = ['Star', 'Plowhorse', 'Puzzle', 'Dog']

export function quadrantColor(quadrant) {
  return QUADRANTS[quadrant]?.color ?? '#8a8178'
}

export function quadrantTextColor(quadrant) {
  return QUADRANTS[quadrant]?.text ?? '#6e6358'
}
