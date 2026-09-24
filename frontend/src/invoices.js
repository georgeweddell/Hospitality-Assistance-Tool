// Invoice review: a live preview of each line's price and checks while the
// owner edits. The backend works everything out again when the invoice is
// applied (backend/invoices.py), so these are only for display.

// Pack unit -> [the base unit it measures, base units per pack unit]
const PACK_BASE = { kg: ['gram', 1000], g: ['gram', 1], l: ['ml', 1000], ml: ['ml', 1], each: ['each', 1] }
export const PACK_UNIT_OPTIONS = Object.keys(PACK_BASE)
const BIG_CHANGE_PERCENT = 25

// Short labels, with the explanation shown on hover.
export const FLAGS = {
  totals: ["Totals don't add up", "Quantity × unit price doesn't match the line total. Check the numbers were read correctly."],
  pack: ['Check pack', "The pack size wasn't read. Enter it as count × size, e.g. 12 × 1 kg."],
  unit: ['Check unit', "The pack's unit doesn't fit how this ingredient is measured (e.g. litres for something weighed)."],
  big_change: ['Big change', `More than ${BIG_CHANGE_PERCENT}% away from the current price. Often a misread pack size.`],
}

const num = (value) => (value === '' || value == null ? null : Number(value))

// The unit a line is priced in: the chosen ingredient's, or the pack's for a new ingredient.
export function lineUnit(line, ingredient) {
  return line.action === 'update' ? ingredient?.unit ?? null : PACK_BASE[line.pack_unit]?.[0] ?? null
}

// £93.60 for 12 × 1 kg -> 93.60 / 12,000 g = £0.0078 per g. Null if it can't be worked out.
export function linePrice(line, unit) {
  const count = num(line.pack_count)
  const size = num(line.pack_size)
  const price = num(line.unit_price)
  const base = PACK_BASE[line.pack_unit]
  if (count == null || size == null || price == null || !base || !(count > 0 && size > 0)) return null
  if (base[0] !== unit) return null
  return price / (count * size * base[1])
}

// Percentage change from the ingredient's current price, or null.
export function changePercent(price, ingredient) {
  if (price == null || !ingredient?.price_per_unit) return null
  return (price / ingredient.price_per_unit - 1) * 100
}

export function lineFlags(line, ingredient) {
  const flags = []
  const quantity = num(line.quantity)
  const unitPrice = num(line.unit_price)
  const total = num(line.line_total)
  if (quantity != null && unitPrice != null && total != null
      && Math.abs(quantity * unitPrice - total) > Math.max(0.01, 0.01 * Math.abs(total))) {
    flags.push('totals')
  }
  if (line.action === 'ignore') return flags

  const unit = lineUnit(line, ingredient)
  if ([line.pack_count, line.pack_size, line.unit_price].some((v) => num(v) == null) || !line.pack_unit) {
    flags.push('pack')
  } else if (unit && PACK_BASE[line.pack_unit][0] !== unit) {
    flags.push('unit')
  }
  const change = changePercent(linePrice(line, unit), line.action === 'update' ? ingredient : null)
  if (change != null && Math.abs(change) > BIG_CHANGE_PERCENT) flags.push('big_change')
  return flags
}

// A review line from the backend -> editable form state (inputs hold strings).
export function toEditable(line, index) {
  const text = (v) => (v == null ? '' : String(v))
  return {
    ...line,
    key: index,
    pack_count: text(line.pack_count),
    pack_size: text(line.pack_size),
    pack_unit: line.pack_unit ?? '',
    unit_price: text(line.unit_price),
    new_ingredient_name: line.new_ingredient_name ?? '',
  }
}

// Editable line -> what POST /imports/invoice/apply expects.
export function applyLine(line) {
  return {
    description: line.description,
    action: line.action,
    ingredient_id: line.action === 'update' ? line.ingredient_id : null,
    new_ingredient_name: line.action === 'new' ? line.new_ingredient_name.trim() : null,
    pack_count: num(line.pack_count),
    pack_size: num(line.pack_size),
    pack_unit: line.pack_unit || null,
    unit_price: num(line.unit_price),
  }
}
