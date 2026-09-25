import { getJson, postFile } from './api'

// What each kind of upload accepts, where it's read, what its review screen
// checks it against, and roughly how long reading takes (seconds, measured with
// the sample files; drives the progress bar). Shared by the Imports and Setup pages.
export const UPLOADS = {
  menu: { accept: '.pdf,.jpg,.jpeg,.png,.webp', route: '/imports/menu/read', options: '/dishes', reading: 'Reading menu…', seconds: 25 },
  invoice: { accept: '.pdf,.jpg,.jpeg,.png,.webp', route: '/imports/invoice/read', options: '/ingredients', reading: 'Reading invoice…', seconds: 15 },
  sales: { accept: '.csv', route: '/imports/sales/read', options: '/dishes', reading: 'Reading sales…', seconds: 8 },
}

// How full the bar is after `elapsed` seconds of a read that usually takes
// `usual`: steady to 90% at the usual time, then creeping towards (never
// reaching) 100%, since Claude doesn't report its own progress.
export function readingPercent(elapsed, usual) {
  if (elapsed <= usual) return (elapsed / usual) * 90
  return 90 + 9 * (1 - Math.exp(-(elapsed - usual) / usual))
}

// Upload a file and get back { kind, review, options } for its review screen.
export function readUpload(kind, file) {
  const { route, options } = UPLOADS[kind]
  return Promise.all([postFile(route, file), getJson(options)])
    .then(([review, list]) => ({ kind, review, options: list }))
}
