// Entering prices the way invoices show them (a pack price), for the price forms.

// Pack units that fit each base unit, and how many base units each holds.
export const PACK_UNITS = {
  gram: [['kg', 1000], ['g', 1]],
  ml: [['l', 1000], ['ml', 1]],
  each: [['each', 1]],
}

export function emptyPrice(unit) {
  return { packPrice: '', packQuantity: '1', packUnit: PACK_UNITS[unit][0][0], supplier: '', source: 'invoice' }
}

// The request body for a price, as the backend expects it. The backend does
// the real conversion to a base-unit price (units.py).
export function priceBody(price) {
  return {
    pack_price: Number(price.packPrice),
    pack_quantity: Number(price.packQuantity),
    pack_unit: price.packUnit,
    source: price.source,
    supplier: price.supplier.trim() || null,
  }
}

export function priceProblem(price) {
  if (price.packPrice === '' || !(Number(price.packPrice) >= 0)) return 'Enter what you paid.'
  if (!(Number(price.packQuantity) > 0)) return 'Enter how much you got for that price.'
  return null
}
