import PublicLayout from './PublicLayout'
import { CONTACT_EMAIL, OWNER } from '../legal'

// The page a signed-out visitor sees at the site's address (App.jsx). One of the
// agreed exceptions to "no explanatory sentences": it says what Docket is.

const STEPS = [
  { name: 'bring your data', text: 'A menu PDF or photo, supplier invoices, a till export. Claude reads them; you check every draft before it is saved.' },
  { name: 'a live menu', text: 'Each dish gets a plate cost and a margin, kept up to date as prices and sales change.' },
  { name: 'what to change', text: 'A ranked list of changes, each with the pounds it would add or save.' },
]

const FEATURES = [
  { label: 'menu engineering', title: 'Star · Plowhorse · Puzzle · Dog', tone: 'tile-tomato corner-tr' },
  { label: 'action list', title: 'Every change ranked in £', tone: 'tile-mustard corner-bl' },
  { label: 'price-rise alerts', title: 'New invoice, new costs', tone: 'tile-basil corner-tl' },
  { label: 'ai report', title: 'Every number from code', tone: 'tile-outline corner-br' },
]

function LandingPage() {
  const invite = `mailto:${CONTACT_EMAIL}?subject=${encodeURIComponent('Docket invite')}`
  return (
    <PublicLayout>
      <div className="space-y-16">
        <section className="grid items-center gap-10 lg:grid-cols-[1fr_1.15fr]">
          <div className="space-y-6">
            <h1 className="page-title">know what every dish earns<span className="text-accent">.</span></h1>
            <p className="doc-lead">
              Docket is a menu and margin engine for small independent UK restaurants. It works out what each
              dish costs to make and what it earns, then says what to change, in pounds.
            </p>
            <div className="flex flex-wrap gap-3">
              <a href="#/login" className="btn btn-primary">Sign in</a>
              <a href={invite} className="btn btn-secondary">Request an invite</a>
            </div>
          </div>
          <img src="/landing/overview.webp" width="1600" height="1075" alt="The Docket overview page for the demo pizzeria"
               className="w-full rounded-[22px] border-2 border-ink" />
        </section>

        <section className="space-y-4">
          <h2 className="section-title">how it works</h2>
          <div>
            <div className="rail" />
            <div className="rail-tickets">
              {STEPS.map((step, i) => (
                <div key={step.name} className="ticket" style={{ '--tilt': `${[-1.5, 1, -0.5][i]}deg` }}>
                  <span className="ticket-clip" />
                  <span className="ticket-meta"><span>step</span><span>{i + 1}</span></span>
                  <p className="ticket-name">{step.name}</p>
                  <p className="m-0 text-sm">{step.text}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="space-y-4">
          <h2 className="section-title">what it does</h2>
          <div className="grid gap-4 sm:grid-cols-2">
            {FEATURES.map((f) => (
              <div key={f.label} className={`tile ${f.tone} min-h-36`}>
                <span className="tile-label">{f.label}</span>
                <span className="ticket-name">{f.title}</span>
              </div>
            ))}
          </div>
        </section>

        <p className="doc-lead">
          Built by {OWNER} as a portfolio project, from time spent line-cooking in a Neapolitan pizzeria.
          Accounts are by invite: <a href={invite} className="link">get in touch</a> for access.
        </p>
      </div>
    </PublicLayout>
  )
}

export default LandingPage
