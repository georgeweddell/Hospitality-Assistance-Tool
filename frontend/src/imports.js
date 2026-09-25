import { getJson, postFile } from './api'

// What each kind of upload accepts, where it's read, and what its review
// screen checks it against. Shared by the Imports and Setup pages.
export const UPLOADS = {
  menu: { accept: '.pdf,.jpg,.jpeg,.png,.webp', route: '/imports/menu/read', options: '/dishes', reading: 'Reading menu…' },
  invoice: { accept: '.pdf,.jpg,.jpeg,.png,.webp', route: '/imports/invoice/read', options: '/ingredients', reading: 'Reading invoice…' },
  sales: { accept: '.csv', route: '/imports/sales/read', options: '/dishes', reading: 'Reading sales…' },
}

// Upload a file and get back { kind, review, options } for its review screen.
export function readUpload(kind, file) {
  const { route, options } = UPLOADS[kind]
  return Promise.all([postFile(route, file), getJson(options)])
    .then(([review, list]) => ({ kind, review, options: list }))
}
