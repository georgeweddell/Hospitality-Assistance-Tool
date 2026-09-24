import { useEffect, useState } from 'react'

// Page navigation using the URL hash (e.g. /#/menu/12). Works on any static
// host without server config, and the browser back button works as expected.
export const PAGES = ['overview', 'actions', 'menu', 'ingredients', 'sales', 'analysis', 'settings']

function currentRoute() {
  const [page, id] = window.location.hash.replace('#/', '').split('/')
  return PAGES.includes(page) ? { page, id: id ? Number(id) : null } : { page: 'overview', id: null }
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
