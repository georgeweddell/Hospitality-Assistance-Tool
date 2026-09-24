// Date ranges for the analysis, as 'YYYY-MM-DD' strings (the API's format).
// All maths is done in UTC so a date never shifts by a day across time zones.

const toDate = (iso) => new Date(`${iso}T00:00:00Z`)
const toISO = (d) => d.toISOString().slice(0, 10)

export function addDays(iso, days) {
  const d = toDate(iso)
  d.setUTCDate(d.getUTCDate() + days)
  return toISO(d)
}

export function monthBounds(iso) {
  const d = toDate(iso)
  const start = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), 1))
  const end = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth() + 1, 0))
  return { from: toISO(start), to: toISO(end) }
}

export function daysBetween(from, to) {
  return Math.round((toDate(to) - toDate(from)) / 86400000) + 1
}

export function eachDay(from, to) {
  const days = []
  for (let d = from; d <= to; d = addDays(d, 1)) days.push(d)
  return days
}

const monthName = (iso) => toDate(iso).toLocaleDateString('en-GB', { month: 'long', year: 'numeric', timeZone: 'UTC' })
const dayMonth = (iso) => toDate(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', timeZone: 'UTC' })
const dayMonthYear = (iso) => toDate(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' })

// "August 2026", or "1 Jun – 31 Aug 2026"
export function rangeLabel({ from, to }) {
  const m = monthBounds(from)
  if (m.from === from && m.to === to) return monthName(from)
  return from.slice(0, 4) === to.slice(0, 4)
    ? `${dayMonth(from)} – ${dayMonthYear(to)}`
    : `${dayMonthYear(from)} – ${dayMonthYear(to)}`
}

// Presets are relative to the latest sale on record, not today, so an older
// dataset still opens on a period that has data.
export function presets(lastSale) {
  const anchor = lastSale ?? toISO(new Date())
  const latest = monthBounds(anchor)
  const previous = monthBounds(addDays(latest.from, -1))
  const threeMonthsStart = monthBounds(addDays(previous.from, -1)).from
  return [
    { key: 'latest-month', label: `Latest month (${monthName(latest.from)})`, ...latest },
    { key: 'previous-month', label: `Previous month (${monthName(previous.from)})`, ...previous },
    { key: 'last-3-months', label: 'Last 3 months', from: threeMonthsStart, to: latest.to },
    { key: 'last-30-days', label: 'Last 30 days of sales', from: addDays(anchor, -29), to: anchor },
    { key: 'last-7-days', label: 'Last 7 days of sales', from: addDays(anchor, -6), to: anchor },
  ]
}

export const rangeQuery = ({ from, to }) => `from=${from}&to=${to}`

export function isFullMonth({ from, to }) {
  const m = monthBounds(from)
  return m.from === from && m.to === to
}

// The period just before this one, to compare against: the previous calendar
// month for a month, otherwise the same number of days immediately before.
export function previousRange(range) {
  if (isFullMonth(range)) return monthBounds(addDays(range.from, -1))
  const days = daysBetween(range.from, range.to)
  return { from: addDays(range.from, -days), to: addDays(range.from, -1) }
}

// "July" for a month, otherwise "the previous 30 days".
export function previousLabel(range) {
  if (!isFullMonth(range)) return `the previous ${daysBetween(range.from, range.to)} days`
  return toDate(previousRange(range).from).toLocaleDateString('en-GB', { month: 'long', timeZone: 'UTC' })
}
