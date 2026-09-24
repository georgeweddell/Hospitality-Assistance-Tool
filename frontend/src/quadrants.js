// One colour per quadrant, shared by the charts, badges and summary, so a Dog
// is the same aubergine everywhere. `text` is a darker shade of the same colour
// for small text on a tinted background (it keeps 4.5:1 contrast).
// `action` is the short label for the Overview's opportunity cards.
export const QUADRANTS = {
  Star: { color: '#2f8a55', text: '#236b41', action: 'Keep and feature' },
  Plowhorse: { color: '#d99612', text: '#855900', action: 'Reprice or re-engineer' },
  Puzzle: { color: '#2f66c8', text: '#2656a8', action: 'Promote' },
  Dog: { color: '#7b3f73', text: '#6e3767', action: 'Review for removal' },
}

export const QUADRANT_ORDER = ['Star', 'Plowhorse', 'Puzzle', 'Dog']

export function quadrantColor(quadrant) {
  return QUADRANTS[quadrant]?.color ?? '#8a8178'
}

export function quadrantTextColor(quadrant) {
  return QUADRANTS[quadrant]?.text ?? '#6e6358'
}
