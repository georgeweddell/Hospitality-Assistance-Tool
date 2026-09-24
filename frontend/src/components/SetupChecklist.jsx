import Hint from './Hint'
import { navigate } from '../useHashRoute'
import { setupSteps } from '../setup'

function go(step) {
  if (step.menuTab) {
    try {
      sessionStorage.setItem('menu-view', JSON.stringify({ category: step.menuTab, status: 'all' }))
    } catch {
      // the Menu page just opens on its default tab
    }
  }
  navigate(step.to)
}

function Tick({ done, n }) {
  return done ? (
    <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-accent text-accent-ink" aria-label="Done">
      <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="3"
           strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M5 12l5 5 9-10" /></svg>
    </span>
  ) : (
    <span className="num flex h-7 w-7 shrink-0 items-center justify-center rounded-full border-2 border-line-strong text-sm font-semibold text-muted">
      {n}
    </span>
  )
}

function SetupChecklist({ status }) {
  const steps = setupSteps(status)
  const required = steps.filter((s) => !s.optional)
  const done = required.filter((s) => s.done).length

  return (
    <section className="card">
      <div className="card-header">
        <h2 className="section-title">Set up</h2>
        <span className="count num">{done} / {required.length}</span>
      </div>
      <ol>
        {steps.map((s, i) => (
          <li key={s.key} className="flex items-center gap-4 border-t border-line px-5 py-3.5">
            <Tick done={s.done} n={i + 1} />
            <span className="flex grow items-center gap-2 font-semibold">
              {s.label}
              {s.optional && <span className="chip chip-muted">Optional</span>}
              {s.hint && <Hint content={s.hint} label={`About ${s.label}`} />}
            </span>
            <span className="num w-20 text-right text-muted">{s.figure}</span>
            <button type="button" onClick={() => go(s)}
                    className={`btn btn-sm w-32 ${!s.done && !s.optional ? 'btn-primary' : 'btn-secondary'}`}>
              {s.action}
            </button>
          </li>
        ))}
      </ol>
    </section>
  )
}

export default SetupChecklist
