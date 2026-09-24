// Places dish-name labels on a scatter chart so they don't overlap each other
// or the dots. Each label tries positions around its dot in order and takes
// the first that's clear and inside the plot; if none is, the least-crowded one.
//
// Works in pixels, from the data values and the plot's size.

const CHAR_WIDTH = 6.6   // average width of a 12px character
const LINE_HEIGHT = 14
const DOT_RADIUS = 7

// Offset of the label's anchor point from the dot, and its text alignment.
const CANDIDATES = [
  { dx: 0, dy: -11, anchor: 'middle' },   // above
  { dx: 11, dy: 4, anchor: 'start' },     // right
  { dx: -11, dy: 4, anchor: 'end' },      // left
  { dx: 0, dy: 19, anchor: 'middle' },    // below
  { dx: 8, dy: -9, anchor: 'start' },     // above right
  { dx: -8, dy: -9, anchor: 'end' },      // above left
  { dx: 8, dy: 17, anchor: 'start' },     // below right
  { dx: -8, dy: 17, anchor: 'end' },      // below left
]

function box(x, y, text, { dx, dy, anchor }) {
  const w = text.length * CHAR_WIDTH
  const left = anchor === 'start' ? x + dx : anchor === 'end' ? x + dx - w : x + dx - w / 2
  const baseline = y + dy
  return { left, right: left + w, top: baseline - LINE_HEIGHT + 3, bottom: baseline + 3 }
}

function overlap(a, b) {
  const w = Math.min(a.right, b.right) - Math.max(a.left, b.left)
  const h = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top)
  return w > 0 && h > 0 ? w * h : 0
}

/**
 * points: [{ key, x, y, text }] in data units.
 * corners: optional { topLeft, topRight, bottomLeft, bottomRight } label texts
 * already drawn in the plot's corners, which labels should avoid.
 * Returns { [key]: { dx, dy, anchor } } for each label.
 */
export function placeLabels(points, { xDomain, yDomain, width, height, corners = {} }) {
  const toPx = (p) => ({
    ...p,
    px: ((p.x - xDomain[0]) / (xDomain[1] - xDomain[0])) * width,
    py: height - ((p.y - yDomain[0]) / (yDomain[1] - yDomain[0])) * height,
  })
  const pts = points.map(toPx)
  const dots = pts.map((p) => ({
    key: p.key,
    left: p.px - DOT_RADIUS, right: p.px + DOT_RADIUS, top: p.py - DOT_RADIUS, bottom: p.py + DOT_RADIUS,
  }))
  // The corner labels (11px bold, 10px in from the edges) count as already placed.
  const cornerBox = (text, atRight, atBottom) => {
    const w = text.length * 8 + 4
    const left = atRight ? width - 10 - w : 10
    const top = atBottom ? height - 10 - LINE_HEIGHT : 10
    return { left, right: left + w, top, bottom: top + LINE_HEIGHT }
  }
  const placed = [
    corners.topLeft && cornerBox(corners.topLeft, false, false),
    corners.topRight && cornerBox(corners.topRight, true, false),
    corners.bottomLeft && cornerBox(corners.bottomLeft, false, true),
    corners.bottomRight && cornerBox(corners.bottomRight, true, true),
  ].filter(Boolean)
  const result = {}

  // Top of the chart first: those labels have the least room above them.
  for (const p of [...pts].sort((a, b) => a.py - b.py)) {
    let best = null
    for (const c of CANDIDATES) {
      const b = box(p.px, p.py, p.text, c)
      const outside = b.left < 0 || b.right > width || b.top < 0 || b.bottom > height
      let crowding = outside ? 1e6 : 0
      for (const other of placed) crowding += overlap(b, other)
      for (const d of dots) if (d.key !== p.key) crowding += overlap(b, d)
      if (!best || crowding < best.crowding) best = { c, b, crowding }
      if (crowding === 0) break
    }
    placed.push(best.b)
    result[p.key] = best.c
  }
  return result
}
