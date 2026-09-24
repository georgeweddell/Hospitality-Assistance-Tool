import { useEffect, useState } from 'react'

// Page navigation using the URL hash (e.g. /#/dishes). Works on any static
// host without server config, and the browser back button works as expected.
export const PAGES = ['overview', 'analysis', 'dishes', 'setup']

function currentPage() {
  const page = window.location.hash.replace('#/', '')
  return PAGES.includes(page) ? page : 'overview'
}

export default function useHashRoute() {
  const [page, setPage] = useState(currentPage)

  useEffect(() => {
    const onChange = () => {
      setPage(currentPage())
      window.scrollTo(0, 0)
    }
    window.addEventListener('hashchange', onChange)
    return () => window.removeEventListener('hashchange', onChange)
  }, [])

  return page
}
