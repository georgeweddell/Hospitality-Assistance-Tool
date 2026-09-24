// App shell: sidebar navigation on desktop, a top bar with tabs on small screens.

const NAV = [
  { page: 'overview', label: 'Overview', icon: 'M4 5h6v6H4zM14 5h6v6h-6zM4 15h6v4H4zM14 15h6v4h-6z' },
  { page: 'menu', label: 'Menu', icon: 'M8 6h12M8 12h12M8 18h12M4 6h.01M4 12h.01M4 18h.01' },
  { page: 'ingredients', label: 'Ingredients', icon: 'M5 11h14l-1.5 8h-11zM8 11V8a4 4 0 0 1 8 0v3' },
  { page: 'sales', label: 'Sales', icon: 'M4 20h16M7 16v-5M12 16V6M17 16v-8' },
  { page: 'analysis', label: 'Insights', icon: 'M4 4v16h16M8 14l3-3 3 2 5-6' },
]

function NavIcon({ path }) {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4 shrink-0" fill="none" stroke="currentColor"
         strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d={path} />
    </svg>
  )
}

function NavLink({ item, active, badge, compact }) {
  const base = compact
    ? 'flex items-center gap-2 whitespace-nowrap rounded-lg px-3 py-1.5 text-sm'
    : 'flex items-center gap-3 rounded-lg px-3 py-2 text-sm'
  const state = active
    ? 'bg-accent/10 font-medium text-accent'
    : 'text-muted hover:bg-bg hover:text-ink'
  return (
    <a href={`#/${item.page}`} className={`${base} ${state}`} aria-current={active ? 'page' : undefined}>
      <NavIcon path={item.icon} />
      {item.label}
      {badge > 0 && (
        <span className="ml-auto rounded-full bg-warn-bg px-1.5 text-xs font-medium text-warn">{badge}</span>
      )}
    </a>
  )
}

function Brand() {
  return (
    <div className="flex items-center gap-2.5">
      <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent text-sm font-bold text-accent-ink">
        M
      </span>
      <span className="font-semibold leading-tight text-ink">Menu &amp; Margin</span>
    </div>
  )
}

function Layout({ page, title, toolbar, badges = {}, children }) {
  return (
    <div className="min-h-screen bg-bg text-ink lg:flex">
      {/* Desktop sidebar */}
      <aside className="hidden w-60 shrink-0 border-r border-line bg-surface lg:block">
        <div className="sticky top-0 flex h-screen flex-col px-4 py-5">
          <Brand />
          <nav className="mt-8 space-y-1">
            {NAV.map((item) => (
              <NavLink key={item.page} item={item} active={page === item.page} badge={badges[item.page]} />
            ))}
          </nav>
        </div>
      </aside>

      {/* Mobile top bar */}
      <header className="border-b border-line bg-surface lg:hidden">
        <div className="px-4 pt-4">
          <Brand />
        </div>
        <nav className="flex gap-1 overflow-x-auto px-3 py-3">
          {NAV.map((item) => (
            <NavLink key={item.page} item={item} active={page === item.page} badge={badges[item.page]} compact />
          ))}
        </nav>
      </header>

      <main className="min-w-0 flex-1">
        <div className="mx-auto max-w-6xl px-4 py-6 sm:px-8 lg:py-8">
          {(title || toolbar) && (
            <div className="mb-6 flex flex-wrap items-start justify-between gap-3">
              {title ? <h1 className="text-2xl font-semibold tracking-tight">{title}</h1> : <span />}
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
