import { useEffect, useState } from 'react'

// Page navigation using the URL hash (e.g. /#/menu/12). Works on any static
// host without server config, and the browser back button works as expected.
export const PAGES = ['overview', 'actions', 'menu', 'ingredients', 'sales', 'imports', 'analysis', 'settings', 'setup', 'reports']
// Pages anyone can open, signed in or not (App.jsx). The landing page is the
// empty hash ('#/' or none), shown only when signed out.
export const PUBLIC_PAGES = ['login', 'privacy', 'terms']
export const LEGAL_PAGES = ['privacy', 'terms']

function currentRoute() {
  const [page, id] = window.location.hash.replace('#/', '').split('/')
  // A numeric id is a record (a dish, a report); a word is a sub-page (reports/suggestions).
  const parsed = !id ? null : /^\d+$/.test(id) ? Number(id) : id
  if (!page) return { page: '', id: null }
  if (PUBLIC_PAGES.includes(page)) return { page, id: null }
  return PAGES.includes(page) ? { page, id: parsed } : { page: 'overview', id: null }
}

export function navigate(path) {
  window.location.hash = `#/${path}`
}

export default function useHashRoute() {
  const [route, setRoute] = useState(currentRoute)

  useEffect(() => {
    const onChange = () => {
      setRoute(currentRoute())
      window.scrollTo(0, 0)
    }
    window.addEventListener('hashchange', onChange)
    return () => window.removeEventListener('hashchange', onChange)
  }, [])

  return route
}
