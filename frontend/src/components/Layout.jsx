// App shell: one header row (wordmark, nav pills, the period picker, settings)
// above the page. Nav labels are lowercase, like the page titles.

const NAV = [
  { page: 'overview', label: 'overview' },
  { page: 'actions', label: 'actions' },
  { page: 'menu', label: 'menu' },
  { page: 'ingredients', label: 'ingredients' },
  { page: 'sales', label: 'sales' },
  { page: 'imports', label: 'imports' },
  { page: 'analysis', label: 'insights' },
]
const SETTINGS = {
  page: 'settings', label: 'Settings',
  icon: 'M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z',
}

function NavIcon({ path }) {
  return (
    <svg viewBox="0 0 24 24" className="h-[18px] w-[18px] shrink-0" fill="none" stroke="currentColor"
         strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d={path} />
    </svg>
  )
}

// The wordmark: "docket" with a tomato full stop.
function Brand() {
  return (
    <a href="#/overview" className="shrink-0 text-[34px] font-extrabold leading-none tracking-[-0.04em] text-ink"
       aria-label="Docket home">
      docket<span className="text-accent">.</span>
    </a>
  )
}

function Layout({ page, title, toolbar, badges = {}, children }) {
  const onSettings = page === 'settings'
  return (
    <div className="min-h-screen bg-bg text-ink">
      {/* One row on wide screens; below xl the nav drops to its own row and scrolls sideways. */}
      <header className="mx-auto flex print:hidden max-w-7xl flex-wrap items-center gap-x-7 gap-y-4 px-4 pt-5 sm:px-10 lg:pt-7">
        <Brand />
        <nav className="tabs order-last w-full xl:order-none xl:w-auto" aria-label="Main">
          {NAV.map((item) => (
            <a key={item.page} href={`#/${item.page}`} className="tab"
               aria-current={page === item.page ? 'page' : undefined}>
              {item.label}
              {badges[item.page] > 0 && <span className="count count-warn">{badges[item.page]}</span>}
            </a>
          ))}
        </nav>
        <div className="ml-auto flex items-center gap-2.5">
          {toolbar}
          <a href={`#/${SETTINGS.page}`} aria-label={SETTINGS.label} title={SETTINGS.label}
             aria-current={onSettings ? 'page' : undefined}
             className={`flex h-11 w-11 items-center justify-center rounded-full border-[1.5px] border-ink ${onSettings ? 'bg-ink text-bg' : 'hover:bg-surface'}`}>
            <NavIcon path={SETTINGS.icon} />
          </a>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 py-7 sm:px-10 lg:py-9">
        {title && <h1 className="page-title mb-8">{title}</h1>}
        {children}
      </main>
    </div>
  )
}

export default Layout
