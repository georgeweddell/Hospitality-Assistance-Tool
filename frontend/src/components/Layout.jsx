// App shell: sidebar navigation on desktop, a top bar with tabs on small screens.

const NAV = [
  { page: 'overview', label: 'Overview', icon: 'M4 5h6v6H4zM14 5h6v6h-6zM4 15h6v4H4zM14 15h6v4h-6z' },
  { page: 'actions', label: 'Actions', icon: 'M9 6h11M9 12h11M9 18h11M4 6l1 1 2-2M4 12l1 1 2-2M4 18l1 1 2-2' },
  { page: 'menu', label: 'Menu', icon: 'M8 6h12M8 12h12M8 18h12M4 6h.01M4 12h.01M4 18h.01' },
  { page: 'ingredients', label: 'Ingredients', icon: 'M5 11h14l-1.5 8h-11zM8 11V8a4 4 0 0 1 8 0v3' },
  { page: 'sales', label: 'Sales', icon: 'M4 20h16M7 16v-5M12 16V6M17 16v-8' },
  { page: 'analysis', label: 'Insights', icon: 'M4 4v16h16M8 14l3-3 3 2 5-6' },
]

function NavIcon({ path }) {
  return (
    <svg viewBox="0 0 24 24" className="h-[18px] w-[18px] shrink-0" fill="none" stroke="currentColor"
         strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d={path} />
    </svg>
  )
}

function NavLink({ item, active, badge, compact }) {
  const base = compact
    ? 'flex items-center gap-2 whitespace-nowrap rounded-lg px-3 py-2'
    : 'flex items-center gap-3 rounded-[10px] px-3 py-2.5'
  const state = active
    ? 'bg-accent-soft font-semibold text-accent-hover'
    : 'font-medium text-muted hover:bg-surface hover:text-ink'
  return (
    <a href={`#/${item.page}`} className={`${base} ${state}`} aria-current={active ? 'page' : undefined}>
      <NavIcon path={item.icon} />
      {item.label}
      {badge > 0 && <span className="count count-warn ml-auto">{badge}</span>}
    </a>
  )
}

// The Docket mark: an order ticket, the slip that runs every kitchen.
function Brand() {
  return (
    <a href="#/overview" className="flex items-center gap-3 px-1.5 text-ink" aria-label="Docket home">
      <svg width="30" height="30" viewBox="0 0 30 30" aria-hidden="true">
        <path d="M7 3h16v24l-4-3-4 3-4-3-4 3z" fill="var(--accent)" />
        <path d="M11 10h8M11 15h8" stroke="var(--surface)" strokeWidth="2" strokeLinecap="round" />
      </svg>
      <span className="font-display text-[26px] font-bold tracking-tight">Docket</span>
    </a>
  )
}

function Layout({ page, title, toolbar, badges = {}, children }) {
  return (
    <div className="min-h-screen bg-bg text-ink lg:flex">
      {/* Desktop sidebar */}
      <aside className="hidden w-[232px] shrink-0 border-r border-line lg:block">
        <div className="sticky top-0 flex h-screen flex-col gap-8 px-[18px] py-7">
          <Brand />
          <nav className="flex flex-col gap-1" aria-label="Main">
            {NAV.map((item) => (
              <NavLink key={item.page} item={item} active={page === item.page} badge={badges[item.page]} />
            ))}
          </nav>
        </div>
      </aside>

      {/* Mobile top bar */}
      <header className="border-b border-line lg:hidden">
        <div className="px-4 pt-4">
          <Brand />
        </div>
        <nav className="flex gap-1 overflow-x-auto px-3 py-3" aria-label="Main">
          {NAV.map((item) => (
            <NavLink key={item.page} item={item} active={page === item.page} badge={badges[item.page]} compact />
          ))}
        </nav>
      </header>

      <main className="min-w-0 flex-1">
        <div className="mx-auto max-w-6xl px-4 py-6 sm:px-10 lg:py-8">
          {(title || toolbar) && (
            <div className="mb-7 flex flex-wrap items-start justify-between gap-4">
              {title ? <h1 className="page-title">{title}</h1> : <span />}
              {toolbar}
            </div>
          )}
          {children}
        </div>
      </main>
    </div>
  )
}

export default Layout
