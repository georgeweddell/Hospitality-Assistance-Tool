import { CONTACT_EMAIL, OWNER } from '../legal'

// The shell for the pages anyone can open (landing, login, privacy, terms):
// the wordmark, one button, and a footer with the legal links.
// signedIn: the header button opens the app instead of the login page.
// bare: no header button (the login page itself).
function PublicLayout({ signedIn = false, bare = false, children }) {
  return (
    <div className="flex min-h-screen flex-col bg-bg text-ink">
      <header className="mx-auto flex w-full max-w-6xl items-center justify-between gap-4 px-4 pt-5 sm:px-10 lg:pt-7">
        <a href={signedIn ? '#/overview' : '#/'} aria-label="Docket home"
           className="text-[34px] font-extrabold leading-none tracking-[-0.04em] text-ink">
          docket<span className="text-accent">.</span>
        </a>
        {!bare && (
          signedIn
            ? <a href="#/overview" className="btn btn-secondary">Open docket</a>
            : <a href="#/login" className="btn btn-secondary">Sign in</a>
        )}
      </header>

      <main className="mx-auto w-full max-w-6xl grow px-4 py-10 sm:px-10">{children}</main>

      <footer className="mx-auto w-full max-w-6xl px-4 sm:px-10">
        <div className="flex flex-wrap items-center gap-x-6 gap-y-2 border-t-2 border-dashed border-line-strong py-6">
          <a href="#/privacy" className="label hover:text-ink">privacy &amp; cookies</a>
          <a href="#/terms" className="label hover:text-ink">terms</a>
          <a href={`mailto:${CONTACT_EMAIL}`} className="label hover:text-ink">contact</a>
          <span className="label ml-auto">© {new Date().getFullYear()} {OWNER}</span>
        </div>
      </footer>
    </div>
  )
}

export default PublicLayout
